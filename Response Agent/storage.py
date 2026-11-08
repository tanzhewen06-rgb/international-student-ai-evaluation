"""Build experiment records and append them to a model's JSONL file."""

from datetime import datetime, timezone
from pathlib import Path
import re
from uuid import uuid4

import models
import prompts
from record_format import (
    RecordDecoder, compact_record, make_header, parse_line, serialize, text_hash,
)


def response_filename(model_name):
    """Use the full model ID without unsafe characters or filename collisions."""
    if not re.fullmatch(r"(?:gemini|gpt|deepseek)-[a-z0-9][a-z0-9._-]*", model_name):
        raise ValueError(
            "Model ID must start with 'gemini-', 'gpt-' or 'deepseek-' and contain only "
            "lowercase letters, numbers, periods, underscores, or hyphens."
        )
    return f"responses_{model_name}.jsonl"


class ExperimentStorage:
    """Keep one run's metadata and open its destination before model requests."""

    def __init__(self, model_name, batch_name, persona_prompt, output_root, scenarios, *, scenario_file=None,
                 persona_file=None, student_background=None, student_background_file=None):
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name must be a non-empty model ID.")
        self.model_name = model_name.strip()
        filename = response_filename(self.model_name)
        if not isinstance(batch_name, str) or not re.fullmatch(r"(?:batch_\d{3,}|Final_Batch_Type_[1-9][0-9]*)", batch_name):
            raise ValueError("batch_name must use a name such as batch_001 or Final_Batch_Type_1.")
        self.run_id = uuid4().hex
        self.response_file = Path(output_root) / batch_name / filename
        self._log = None
        self._lock = self.response_file.with_suffix(".jsonl.lock")
        self._seen_ids = set()
        # main.py passes the selected file; older callers retain their defaults.
        selected_scenario = Path(scenario_file) if scenario_file is not None else prompts.SCENARIO_PROMPT_PATH
        version_match = re.search(r"(?:^|[ _-])(?:V|Version[ _-]*)([1-9][0-9]*(?:\.[0-9]+)*)$", selected_scenario.stem, re.IGNORECASE)
        selected_version = (f"V{version_match[1]}" if version_match else "unversioned") if scenario_file is not None else prompts.SCENARIO_VERSION
        selected_persona = Path(persona_file) if persona_file is not None else prompts.PERSONA_PROMPT_PATH
        persona_match = re.search(r"(?:^|[ _-])(?:V|Version[ _-]*)([1-9][0-9]*)$", selected_persona.stem, re.IGNORECASE)
        persona_version = (f"V{persona_match[1]}" if persona_match else "unversioned") if persona_file is not None else prompts.PERSONA_VERSION
        self._metadata = {
            "schema_version": 1,
            "batch_name": batch_name,
            "model_name": self.model_name,
            "generation_config": (
                dict(models.GENERATION_CONFIGS.get(self.model_name, {}))
                if self.model_name.startswith(("gemini-", "deepseek-")) else {}
            ),
            "persona_id": "international_student_counselor",
            "persona_version": persona_version,
            "persona_file": selected_persona.name,
            "persona_prompt": persona_prompt,
            "persona_sha256": text_hash(persona_prompt),
            "scenario_version": selected_version,
            "scenario_file": selected_scenario.name,
        }
        if student_background is not None:
            if not isinstance(student_background, str) or not student_background.strip():
                raise ValueError("student_background must be non-empty text, or None.")
            if student_background_file is None:
                raise ValueError("Provide the background source filename with its text.")
            background_path = Path(student_background_file)
            background_match = re.search(r"(?:^|[ _-])(?:V|Version[ _-]*)([1-9][0-9]*)$", background_path.stem, re.IGNORECASE)
            self._metadata.update(
                student_background_file=background_path.name,
                student_background_version=f"V{background_match[1]}" if background_match else "unversioned",
                student_background_prompt=student_background,
                student_background_sha256=text_hash(student_background),
            )
        elif student_background_file is not None:
            raise ValueError("Background source filename was provided without its text.")
        self._header = make_header(self._metadata, {
            f"scenario_{index}": {
                "scenario_name": name, "scenario_prompt": text,
                "scenario_sha256": text_hash(text),
            }
            for index, (name, text) in enumerate(scenarios.items(), 1)
        })

    def __enter__(self):
        self.response_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._lock.open("x", encoding="utf-8") as lock:
                lock.write(self.run_id + "\n")
        except FileExistsError as exc:
            raise ValueError(f"Response file is already in use: {self._lock}. Remove a stale lock only after the previous run has stopped.") from exc
        try:
            has_content = self.response_file.exists() and self.response_file.stat().st_size > 0
            if has_content:
                with self.response_file.open("rb") as existing_log:
                    existing_log.seek(-1, 2)
                    if existing_log.read(1) != b"\n":
                        raise ValueError(f"Response log ends with an incomplete line: {self.response_file}")
                decoder = RecordDecoder()
                with self.response_file.open(encoding="utf-8-sig") as stream:
                    for line in stream:
                        if not line.strip():
                            continue
                        record = decoder.decode(parse_line(line))
                        if record is not None:
                            compact_record(self._header, record)
                            identifier = record["response_id"]
                            if identifier in self._seen_ids:
                                raise ValueError(f"Duplicate response_id: {identifier}")
                            self._seen_ids.add(identifier)
                if decoder.header != self._header:
                    raise ValueError("Saved file is legacy or its prompts/settings differ. Use a new batch or convert the legacy file before appending.")
            self._log = self.response_file.open("a", encoding="utf-8", newline="\n")
            if not has_content:
                self._log.write(serialize(self._header))
                self._log.flush()
        except BaseException:
            if self._log is not None:
                self._log.close()
            self._lock.unlink()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self._log.close()
        finally:
            self._lock.unlink()

    def new_record(self, scenario_index, scenario_name, scenario, user_prompt, repeat_index):
        """Capture a request's start time, exact input, and unique ID."""
        return {
            **self._metadata,
            "run_id": self.run_id,
            "response_id": uuid4().hex,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "scenario_id": f"scenario_{scenario_index}",
            "scenario_name": scenario_name,
            "scenario_prompt": scenario,
            "user_prompt": user_prompt,
            "scenario_sha256": text_hash(scenario),
            "repeat_index": repeat_index,
            "response_text": None,
            "status": "error",
            "duration_seconds": None,
            "error": None,
        }

    def save(self, record, response_text, error, duration_seconds):
        """Save one success or failure immediately; propagate disk errors."""
        record["status"] = "success" if error is None else "error"
        record["response_text"] = response_text
        record["error"] = (
            {"type": type(error).__name__, "message": str(error)}
            if error is not None else None
        )
        record["duration_seconds"] = round(duration_seconds, 3)
        if record["response_id"] in self._seen_ids:
            raise ValueError(f"Duplicate response_id: {record['response_id']}")
        self._log.write(serialize(compact_record(self._header, record)))
        self._log.flush()
        self._seen_ids.add(record["response_id"])
