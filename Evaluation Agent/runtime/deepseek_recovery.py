"""DeepSeek retry transport with durable, bounded provider diagnostics."""
from datetime import datetime, timezone
import hashlib
from runtime import portable_json as json
from pathlib import Path
import re
import time
import uuid

from versions.v4_12.client import deepseek_key, _usage
from versions.v4_12.judgment import output_schema


def make_model(model_name, config, diagnostics_folder, timeout_seconds=900):
    if not model_name.startswith('deepseek-'):
        raise ValueError('The diagnostic transport supports DeepSeek judges only.')
    if type(timeout_seconds) is not int or not 300 <= timeout_seconds <= 1800:
        raise ValueError('DeepSeek timeout must be between 300 and 1800 seconds.')
    config = dict(config)
    folder = Path(diagnostics_folder)

    def call(model, prompt, instructions):
        if model != model_name:
            raise ValueError('Judge model changed during recovery.')
        counts = re.findall(r'<checklist_output_count>([345])</checklist_output_count>', instructions)
        if len(counts) != 1:
            raise ValueError('Missing exact original checklist count before provider call.')
        from openai import OpenAI
        request = dict(model=model, input=prompt, instructions=instructions,
                       reasoning={'effort': config['reasoning_effort']},
                       max_output_tokens=config['max_output_tokens'],
                       text={'format': {'type': 'json_schema', 'name': 'evaluation_v412',
                                        'schema': output_schema(int(counts[0]))}})
        if config['reasoning_effort'] == 'none':
            request['temperature'] = config['temperature']
        diagnostic = {
            'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'model': model,
            'timeout_seconds': timeout_seconds, 'max_output_tokens': config['max_output_tokens'],
            'reasoning_effort': config['reasoning_effort'], 'fresh_request': True,
            'task_sha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
            'instructions_sha256': hashlib.sha256(instructions.encode('utf-8')).hexdigest()}
        started = time.perf_counter()
        client = None
        try:
            client = OpenAI(api_key=deepseek_key(), base_url=config['base_url'],
                            timeout=timeout_seconds, max_retries=0)
            result = client.responses.create(**request)
            status = getattr(result, 'status', None)
            details = _usage(getattr(result, 'incomplete_details', None))
            provider_error = _usage(getattr(result, 'error', None))
            raw = _usage(getattr(result, 'usage', None))
            output = raw.get('output_tokens')
            thinking = (raw.get('output_tokens_details') or {}).get('reasoning_tokens')
            usage = {'input_tokens': raw.get('input_tokens'),
                     'cached_input_tokens': (raw.get('input_tokens_details') or {}).get('cached_tokens'),
                     'output_tokens': output - thinking if type(output) is int and type(thinking) is int else None,
                     'thinking_tokens': thinking, 'billable_output_tokens': output,
                     'total_tokens': raw.get('total_tokens')}
            diagnostic.update(provider_status=status, incomplete_reason=details.get('reason'),
                              provider_error_code=provider_error.get('code'), usage=usage,
                              response_id=getattr(result, 'id', None),
                              output_text_characters=len(getattr(result, 'output_text', '') or ''))
            if status not in (None, 'completed'):
                print(f"DeepSeek returned {status}; reason={details.get('reason')}; "
                      f"output tokens={output}. Diagnostic saved separately.", flush=True)
                raise RuntimeError('DeepSeek returned an incomplete or failed response; see provider diagnostics.')
            return {'text': result.output_text, 'provider_status': status,
                    'provider_model': getattr(result, 'model', None), 'usage': usage}
        except Exception as exc:
            diagnostic.update(exception_type=type(exc).__name__,
                              api_status_code=getattr(exc, 'status_code', None))
            raise
        finally:
            diagnostic['duration_seconds'] = time.perf_counter() - started
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / ('request_' + uuid.uuid4().hex + '.json')
            path.write_text(json.dumps(diagnostic, indent=2) + '\n', encoding='utf-8')
            if client is not None:
                client.close()

    return call, config
