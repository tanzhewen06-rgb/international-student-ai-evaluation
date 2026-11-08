"""Send one student scenario using the selected AI persona."""

from models import call_model
import prompts
from record_format import build_user_prompt


def build_scenario_prompt(scenario, student_background=None):
    """Build the exact user input used by the model and experiment record."""
    return build_user_prompt(scenario, student_background)


def run_agent(model_name, scenario, system_prompt=None, student_background=None):
    user_prompt = build_scenario_prompt(scenario, student_background)
    if system_prompt is None:
        system_prompt = prompts.load_persona_prompt()
    return call_model(
        model_name=model_name,
        prompt=user_prompt,
        system_prompt=system_prompt,
    )
