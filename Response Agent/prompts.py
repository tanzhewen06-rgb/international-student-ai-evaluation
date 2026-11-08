"""Load persona and scenario Markdown files from the prompts folder."""

from pathlib import Path
import re

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

PERSONA_PROMPT_PATH = PROMPTS_DIR / "international_student_counselor_prompt_en V1.md"
SCENARIO_PROMPT_PATH = PROMPTS_DIR / "international_student_scenario_prompts V1.md"
PERSONA_VERSION = "V1"
SCENARIO_VERSION = "V1"


def load_persona_prompt(path=None):
    """Read the current persona file each time; do not cache the prompt."""
    prompt_path = Path(path) if path is not None else PERSONA_PROMPT_PATH
    try:
        text = prompt_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"AI Persona file not found: {prompt_path}. "
            "Place the persona Markdown file in the prompts folder."
        ) from exc
    if not text.strip():
        raise ValueError(f"AI Persona file is empty: {prompt_path}")
    return text


def load_scenarios(path=None):
    """Read one scenario per ## heading, preserving file order and body text.

    The document title and introduction are not sent to the model. Each unique
    ## heading labels a scenario; its nonempty body is the actual user prompt.
    """
    prompt_path = Path(path) if path is not None else SCENARIO_PROMPT_PATH
    try:
        text = prompt_path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Scenario file not found: {prompt_path}. "
            "Place the scenario Markdown file in the prompts folder."
        ) from exc
    if not text.strip():
        raise ValueError(f"Scenario file is empty: {prompt_path}")

    headings = list(re.finditer(r"^##[ \t]+([^\r\n]+)$", text, re.MULTILINE))
    if not headings:
        raise ValueError(f"No scenarios found in {prompt_path}; use a ## heading for each scenario.")

    scenarios = {}
    for index, heading in enumerate(headings):
        name = heading.group(1).strip()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end():end].strip()
        if not name:
            raise ValueError(f"Scenario heading is empty in {prompt_path}")
        if name in scenarios:
            raise ValueError(f"Duplicate scenario heading {name!r} in {prompt_path}")
        if not body:
            raise ValueError(f"Scenario {name!r} has no prompt text in {prompt_path}")
        scenarios[name] = body
    return scenarios


def load_student_background(path):
    """Load a selected student profile; disabling it is handled by main.py."""
    background_path = Path(path)
    text = background_path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError(f"Student background file is empty: {background_path}")
    return text
