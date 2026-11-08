# ## Models.py


import os

# API keys are read from the environment or Windows Credential Manager.
ENV_NAMES = {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY", "deepseek": "DEEPSEEK_API_KEY"}

# Settings can differ between models. Other models use their API defaults.
GENERATION_CONFIGS = {
    "deepseek-flash": {
        "reasoning_effort": "none",
        "max_output_tokens": 4096,
        "sdk_max_retries": 0,
    },
    "gemini-3.8-flash": {
        "thinking_level": "low",
    },
    "gemini-3.1-pro-preview": {
        "thinking_level": "low",
    },
}


def _get_api_key(provider):
    key = os.environ.get(ENV_NAMES[provider])
    if key:
        return key

    try:
        from keyring.backends.Windows import WinVaultKeyring
    except ImportError as exc:
        raise RuntimeError(
            "Missing keyring dependency. Install requirements.txt using the project Python."
        ) from exc

    key = WinVaultKeyring().get_password("AI Persona Analysis", ENV_NAMES[provider])
    if not key:
        raise RuntimeError(
            f"No saved {ENV_NAMES[provider]}. Run setup_keys.py once to save your key "
            "in Windows Credential Manager."
        )
    return key


def call_gemini(model_name, prompt, system_prompt):
    from google import genai

    client = genai.Client(api_key=_get_api_key("gemini"))
    try:
        response = client.interactions.create(
            model=model_name,
            input=prompt,
            system_instruction=system_prompt,
            generation_config=GENERATION_CONFIGS.get(model_name, {}),
            timeout=300,
        )
        return response.output_text
    finally:
        client.close()


def call_gpt(model_name, prompt, system_prompt):
    from openai import OpenAI

    client = OpenAI(api_key=_get_api_key("openai"), timeout=300)
    try:
        response = client.responses.create(
            model=model_name,
            input=prompt,
            instructions=system_prompt,
        )
        return response.output_text
    finally:
        client.close()


def check_credentials(model_names):
    """Read saved credentials before any collection; do not print keys or make requests."""
    providers=set()
    for name in model_names:
        if name.startswith("gpt-"):providers.add("openai")
        elif name.startswith("gemini-"):providers.add("gemini")
        elif name == "deepseek-flash":providers.add("deepseek")
        else:raise ValueError("Use a configured GPT/Gemini model or the current deepseek-flash.")
    for provider in providers:_get_api_key(provider)


def call_deepseek(model_name, prompt, system_prompt):
    """Use the already-tested DeepSeek Responses endpoint, without grading schema."""
    if model_name != "deepseek-flash":
        raise ValueError("Only the existing deepseek-flash is configured for collection.")
    from openai import OpenAI
    config=GENERATION_CONFIGS[model_name]
    client=OpenAI(api_key=_get_api_key("deepseek"),base_url="https://api.deepseek.com",timeout=300,max_retries=config["sdk_max_retries"])
    try:
        response=client.responses.create(model=model_name,input=prompt,instructions=system_prompt,
            reasoning={"effort":config["reasoning_effort"]},max_output_tokens=config["max_output_tokens"])
        if getattr(response,"status",None) not in (None,"completed"):
            raise RuntimeError("DeepSeek did not complete the response; partial text is not a successful answer.")
        return response.output_text
    finally:
        client.close()


def call_model(model_name, prompt, system_prompt=""):
    """One entry point: switch models by changing the full model ID."""
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name must be a non-empty model ID.")
    model_name = model_name.strip()

    if model_name.startswith("gemini-"):
        text = call_gemini(model_name, prompt, system_prompt)
    elif model_name.startswith("gpt-"):
        text = call_gpt(model_name, prompt, system_prompt)
    elif model_name.startswith("deepseek-"):
        text = call_deepseek(model_name, prompt, system_prompt)
    else:
        raise ValueError(
            f"Unsupported model ID: {model_name!r}. "
            "Use a full text model ID starting with 'gemini-', 'gpt-' or the configured 'deepseek-flash'."
        )

    if not isinstance(text, str) or not text.strip():
        raise RuntimeError(f"{model_name} returned no text response.")
    return text
