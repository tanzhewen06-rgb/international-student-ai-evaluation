"""Load an evaluator-only supplement and bind it to exact saved scenarios."""

import hashlib
from pathlib import Path
import re

from runtime.agent import parse_json, DIMENSIONS


def load_integrated_checklist(instructions):
    """Inspect an inline V3 checklist without appending another supplement."""
    heading = re.search(r"(?m)^## Integrated Checklist V2:[^\r\n]*", instructions)
    if heading is None:
        return None
    following = re.search(r"(?m)^## ", instructions[heading.end():])
    end = heading.end() + following.start() if following else len(instructions)
    text = instructions[heading.start():end]
    rows = re.findall(r"(?m)^\|\s*([GELCAS][1-9][0-9]*)\s*\|\s*D([1-6])\s*\|", text)
    ids = {}
    for checkpoint_id, number in rows:
        if checkpoint_id in ids:
            raise ValueError(f"Duplicate integrated checklist ID: {checkpoint_id}")
        ids[checkpoint_id] = DIMENSIONS[int(number) - 1]
    if not ids or set(ids.values()) != set(DIMENSIONS):
        raise ValueError("Integrated checklist must define IDs and primary dimensions for all six dimensions.")
    return {"text": text, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "id_dimensions": ids}


def load_checklist(path):
    path = Path(path)
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    bindings_matches = list(re.finditer(r"<!-- checklist-bindings\s*\n(.*?)\n-->", text, re.DOTALL))
    if len(bindings_matches) != 1:
        raise ValueError("Checklist must have exactly one checklist-bindings JSON comment.")
    match = bindings_matches[0]
    bindings = parse_json(match[1])
    if not isinstance(bindings, dict) or not bindings:
        raise ValueError("Checklist bindings must be a nonempty scenario-ID to SHA-256 object.")
    for scenario_id, digest in bindings.items():
        if not re.fullmatch(r"scenario_[1-9][0-9]*", scenario_id) or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Checklist bindings require scenario_N IDs and lowercase SHA-256 hashes.")
    text = text[:match.start()] + text[match.end():]
    headings = list(re.finditer(r"(?m)^## ([^\r\n]+)$", text))
    common = [text[:headings[0].start()].strip()] if headings else []
    sections = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        section = text[heading.start():end].strip()
        scenario = re.fullmatch(r"Scenario ([1-9][0-9]*): .+", heading[1])
        if scenario:
            scenario_id = "scenario_" + scenario[1]
            if scenario_id in sections:
                raise ValueError(f"Duplicate checklist section: {scenario_id}")
            body = text[heading.end():end].strip()
            if not body:
                raise ValueError(f"Empty checklist section: {scenario_id}")
            sections[scenario_id] = section
        else:
            common.append(section)
    if set(bindings) != set(sections):
        raise ValueError("Checklist scenario sections and binding IDs must match exactly.")
    # The final consistency check remains after the selected scenario section.
    final = [section for section in common if section.startswith("## Final consistency check\n")]
    common = [section for section in common if section not in final]
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bindings": bindings,
            "common": "\n\n".join(common), "sections": sections,
            "final": "\n\n".join(final)}


def prepare_checklist(checklist, record):
    scenario_id = record.get("scenario_id")
    if not isinstance(scenario_id, str) or scenario_id not in checklist["bindings"]:
        raise ValueError(f"No checklist section is bound to scenario ID {scenario_id!r}.")
    text = record.get("scenario_prompt")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest() if isinstance(text, str) else None
    if digest != checklist["bindings"][scenario_id]:
        raise ValueError(f"Checklist does not match saved scenario text for {scenario_id}; select a compatible checklist or disable it.")
    if record.get("scenario_sha256") not in (None, digest):
        raise ValueError(f"Saved scenario hash does not match its text: {scenario_id}")
    instructions = "\n\n## Scenario-specific evaluation supplement\n\n" + "\n\n".join(
        part for part in (checklist["common"], checklist["sections"][scenario_id], checklist["final"]) if part
    )
    return {"scenario_id": scenario_id, "scenario_sha256": digest,
            "instructions": instructions,
            "instructions_sha256": hashlib.sha256(instructions.encode("utf-8")).hexdigest()}
