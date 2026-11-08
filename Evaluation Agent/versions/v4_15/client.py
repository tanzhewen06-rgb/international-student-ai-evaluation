from pathlib import Path
import hashlib

from gpt_judge_stability import client as gpt
from runtime.paths import RESPONSE_AGENT_ROOT
from versions.v4_12.client import deepseek_key, _usage
from .protocol import schema, FLOW_REVISION

def make_model(model):
    module = gpt.model_layer(RESPONSE_AGENT_ROOT)
    if model == gpt.MODEL:
        key = module._get_api_key('openai')
        config = dict(gpt.CONFIG)
    elif model.startswith('deepseek-'):
        key = deepseek_key()
        config = {'base_url': 'https://api.deepseek.com', 'reasoning_effort': 'none', 'temperature': 0,
                  'max_output_tokens': 4096, 'output_format': 'json_schema', 'sdk_max_retries': 0}
    elif model.startswith('gemini-'):
        key = module._get_api_key('gemini')
        config = dict(module.GENERATION_CONFIGS.get(model, {}))
        config.update(max_output_tokens=4096, temperature=0)
    else:
        raise ValueError('Select the existing tested GPT, Gemini or DeepSeek judge.')
    settings = {**config, 'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'protocol': 'V4.15', 'workflow_revision': FLOW_REVISION}

    def call(requested, prompt, instructions, stage, item_count):
        if requested != model:
            raise ValueError('Judge changed during a configured evaluation.')
        output = schema(stage, item_count)
        if model.startswith('gemini-'):
            from google import genai
            client = genai.Client(api_key=key)
            try:
                response = client.interactions.create(model=model, input=prompt, system_instruction=instructions,
                    generation_config=config, response_format={'type': 'text', 'mime_type': 'application/json', 'schema': output}, timeout=300)
                status = getattr(response, 'status', None)
                if status not in (None, 'completed') or not getattr(response, 'output_text', None):
                    raise RuntimeError('Provider returned an incomplete stage response.')
                raw = _usage(getattr(response, 'usage', None))
                usage = {k: raw.get(v) for k, v in [('input_tokens', 'total_input_tokens'), ('cached_input_tokens', 'total_cached_tokens'),
                    ('output_tokens', 'total_output_tokens'), ('thinking_tokens', 'total_thought_tokens'), ('total_tokens', 'total_tokens')]}
                usage['billable_output_tokens'] = usage['output_tokens'] + usage['thinking_tokens'] if type(usage['output_tokens']) is int and type(usage['thinking_tokens']) is int else None
                return {'text': response.output_text, 'provider_model': getattr(response, 'model', None), 'provider_status': status, 'usage': usage}
            finally:
                client.close()
        from openai import OpenAI
        options = {'api_key': key, 'timeout': 300, 'max_retries': 0}
        if model.startswith('deepseek-'):
            options['base_url'] = config['base_url']
        client = OpenAI(**options)
        try:
            response_format = {'type': 'json_schema', 'name': 'evaluation_v415_' + stage, 'schema': output}
            if model == gpt.MODEL:
                response_format['strict'] = False
            response = client.responses.create(model=model, input=prompt, instructions=instructions,
                reasoning={'effort': config['reasoning_effort']}, temperature=config['temperature'],
                max_output_tokens=config['max_output_tokens'], text={'format': response_format})
            if getattr(response, 'status', None) != 'completed' or not getattr(response, 'output_text', None):
                raise RuntimeError('Provider returned an incomplete stage response.')
            raw = _usage(getattr(response, 'usage', None))
            total = raw.get('output_tokens')
            thinking = (raw.get('output_tokens_details') or {}).get('reasoning_tokens')
            usage = {'input_tokens': raw.get('input_tokens'), 'cached_input_tokens': (raw.get('input_tokens_details') or {}).get('cached_tokens'),
                     'output_tokens': total - thinking if type(total) is int and type(thinking) is int else None,
                     'thinking_tokens': thinking, 'billable_output_tokens': total, 'total_tokens': raw.get('total_tokens')}
            return {'text': response.output_text, 'provider_model': getattr(response, 'model', None), 'provider_status': response.status, 'usage': usage}
        finally:
            client.close()
    return call, settings
