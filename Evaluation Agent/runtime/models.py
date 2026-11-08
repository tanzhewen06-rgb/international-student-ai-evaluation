"""Reuse the Response Agent's API clients and saved credentials."""

import importlib.util
import re


def load_model_layer(response_agent_dir, model_name, compact=False):
    if not isinstance(model_name, str) or not re.fullmatch(r"(?:gpt|gemini|deepseek)-[A-Za-z0-9._-]+", model_name):
        raise ValueError("Use a full gpt-, gemini- or deepseek- model ID containing letters, numbers, dots, underscores or hyphens.")
    path = response_agent_dir / "models.py"
    spec = importlib.util.spec_from_file_location("_response_agent_api_clients", path)
    if spec is None or spec.loader is None:
        raise ValueError("Could not load Response Agent/models.py.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if compact=='V4.12':
        from versions.v4_12.client import make_model
        return make_model(module,model_name)
    if compact=='V4.11':
        from versions.v4_11.client import make_model
        return make_model(module,model_name)
    if compact=='V4.10':
        from versions.v4_10.client import make_model
        return make_model(module,model_name)
    if compact=='V4.9':
        from versions.v4_9.client import make_model
        return make_model(module,model_name)
    if compact=='V4.8':
        from versions.v4_8.client import make_model
        return make_model(module,model_name)
    if compact=='V4.7':
        from versions.v4_7.client import make_model
        return make_model(module,model_name)
    if compact:
        from versions.v4_6.client import make_model
        return make_model(module,model_name)
    return module.call_model, dict(module.GENERATION_CONFIGS.get(model_name, {}))
