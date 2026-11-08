"""Compact JSONL v2: one immutable prompt header, followed by response rows.

Expansion returns the original v1 logical record without changing any text or ID.
Both agents use this module; it performs no model requests or file mutations.
"""

from copy import deepcopy
import hashlib
import json


COMMON_FIELDS = (
    "schema_version", "batch_name", "model_name", "generation_config",
    "persona_id", "persona_version", "persona_file", "persona_prompt",
    "persona_sha256", "scenario_version", "scenario_file",
)
BACKGROUND_FIELDS = (
    "student_background_file", "student_background_version",
    "student_background_prompt", "student_background_sha256",
)
SCENARIO_FIELDS = ("scenario_name", "scenario_prompt", "scenario_sha256")
RESPONSE_FIELDS = (
    "response_id", "run_id", "timestamp_utc", "scenario_id", "repeat_index",
    "response_text", "status", "duration_seconds", "error",
)
USER_PROMPT_PREFIX = "Scenario:\n"


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_user_prompt(scenario, student_background=None):
    if not isinstance(scenario, str) or not scenario.strip():
        raise ValueError("scenario must be non-empty text.")
    if student_background is None:
        return USER_PROMPT_PREFIX + scenario
    if not isinstance(student_background, str) or not student_background.strip():
        raise ValueError("student_background must be non-empty text, or None.")
    return "Student Background:\n" + student_background + "\n\n" + USER_PROMPT_PREFIX + scenario


def prompt_prefix(record):
    """Validate optional profile provenance and reconstruct the exact saved prefix."""
    present = set(BACKGROUND_FIELDS) & set(record)
    if not present:
        return USER_PROMPT_PREFIX
    if present != set(BACKGROUND_FIELDS):
        raise ValueError("Student background metadata must include all four fields.")
    if any(not isinstance(record[field], str) or not record[field].strip() for field in BACKGROUND_FIELDS):
        raise ValueError("Student background fields must be non-empty strings.")
    if text_hash(record["student_background_prompt"]) != record["student_background_sha256"]:
        raise ValueError("Student background hash does not match its saved text.")
    return "Student Background:\n" + record["student_background_prompt"] + "\n\n" + USER_PROMPT_PREFIX


def parse_line(line):
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"Invalid JSON constant: {value}")

    return json.loads(line, object_pairs_hook=unique_object, parse_constant=reject_constant)


def serialize(record):
    return json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"


class HeaderError(ValueError):
    """The entire file must be inspected before any response can be used."""


def validate_header(header):
    expected = {"record_type", "schema_version", "common", "scenarios", "user_prompt_prefix"}
    if not isinstance(header, dict) or set(header) != expected:
        raise HeaderError("Invalid compact metadata header fields.")
    if header["record_type"] != "metadata" or type(header["schema_version"]) is not int or header["schema_version"] != 2:
        raise HeaderError("Expected compact JSONL metadata schema_version 2.")
    common = header["common"]
    if not isinstance(common, dict) or set(common) not in (set(COMMON_FIELDS), set(COMMON_FIELDS) | set(BACKGROUND_FIELDS)):
        raise HeaderError("Missing or unexpected common metadata fields.")
    if type(common["schema_version"]) is not int or common["schema_version"] != 1:
        raise HeaderError("Unsupported expanded record schema version.")
    if not isinstance(common["generation_config"], dict):
        raise HeaderError("generation_config must be an object.")
    for field in set(COMMON_FIELDS) - {"schema_version", "generation_config"}:
        if not isinstance(common[field], str) or not common[field].strip():
            raise HeaderError(f"common.{field} must be a non-empty string.")
    if text_hash(common["persona_prompt"]) != common["persona_sha256"]:
        raise HeaderError("Persona prompt hash does not match its saved text.")
    try:
        expected_prefix = prompt_prefix(common)
    except ValueError as exc:
        raise HeaderError(str(exc)) from exc
    if header["user_prompt_prefix"] != expected_prefix:
        raise HeaderError("User prompt prefix does not match the saved background context.")
    scenarios = header["scenarios"]
    if not isinstance(scenarios, dict) or not scenarios:
        raise HeaderError("The header must contain its saved scenarios.")
    for scenario_id, scenario in scenarios.items():
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise HeaderError("Scenario IDs must be non-empty strings.")
        if not isinstance(scenario, dict) or set(scenario) != set(SCENARIO_FIELDS):
            raise HeaderError(f"Invalid fields for {scenario_id}.")
        if any(not isinstance(value, str) or not value.strip() for value in scenario.values()):
            raise HeaderError(f"Invalid text for {scenario_id}.")
        if text_hash(scenario["scenario_prompt"]) != scenario["scenario_sha256"]:
            raise HeaderError(f"Scenario prompt hash mismatch: {scenario_id}.")


def make_header(common, scenarios):
    header = {
        "record_type": "metadata", "schema_version": 2,
        "common": deepcopy(common), "scenarios": deepcopy(scenarios),
        "user_prompt_prefix": prompt_prefix(common),
    }
    validate_header(header)
    return header


def expand_record(header, row):
    if not isinstance(row, dict) or set(row) != set(RESPONSE_FIELDS) | {"record_type"}:
        raise ValueError("Invalid compact response fields; shared metadata cannot be overridden.")
    if row["record_type"] != "response":
        raise ValueError("Expected record_type=response after the metadata header.")
    scenario_id = row["scenario_id"]
    if not isinstance(scenario_id, str) or scenario_id not in header["scenarios"]:
        raise ValueError(f"Unknown scenario_id: {scenario_id!r}.")
    scenario = header["scenarios"][scenario_id]
    return {
        **deepcopy(header["common"]), **deepcopy(scenario),
        **{field: deepcopy(row[field]) for field in RESPONSE_FIELDS},
        "user_prompt": header["user_prompt_prefix"] + scenario["scenario_prompt"],
    }


def compact_record(header, record):
    """Refuse to drop fields or change shared settings while compacting a row."""
    expected = set(header["common"]) | set(SCENARIO_FIELDS) | set(RESPONSE_FIELDS) | {"user_prompt"}
    if not isinstance(record, dict) or set(record) != expected:
        raise ValueError("Unexpected expanded record fields; conversion would lose data.")
    row = {"record_type": "response", **{field: record[field] for field in RESPONSE_FIELDS}}
    if expand_record(header, row) != record:
        raise ValueError("Record differs from the saved persona, scenarios or settings; use a new batch.")
    return row


def header_from_records(records):
    if not records:
        raise ValueError("Cannot infer a metadata header from an empty response list.")
    common = {field: records[0][field] for field in COMMON_FIELDS}
    common.update({field: records[0][field] for field in BACKGROUND_FIELDS if field in records[0]})
    scenarios = {}
    for record in records:
        scenario = {field: record[field] for field in SCENARIO_FIELDS}
        scenario_id = record["scenario_id"]
        if scenario_id in scenarios and scenarios[scenario_id] != scenario:
            raise ValueError(f"Conflicting snapshots for {scenario_id}; use separate batches.")
        scenarios[scenario_id] = scenario
    header = make_header(common, scenarios)
    for record in records:
        compact_record(header, record)
    return header


class RecordDecoder:
    """Read v1 expanded files or v2 compact files, rejecting mixed formats."""

    def __init__(self):
        self.mode = None
        self.header = None

    def decode(self, value):
        if not isinstance(value, dict):
            raise ValueError("Each JSONL record must be an object.")
        kind = value.get("record_type")
        if kind == "metadata":
            if self.mode is not None:
                raise HeaderError("Metadata must appear once, before all response rows.")
            validate_header(value)
            self.header = value
            self.mode = "compact"
            return None
        if kind == "response":
            if self.mode != "compact":
                raise HeaderError("Compact response has no preceding metadata header.")
            return expand_record(self.header, value)
        if self.mode == "compact" or kind is not None or value.get("schema_version", 1) != 1:
            raise ValueError("Mixed or unsupported JSONL record format.")
        self.mode = "legacy"
        return value
