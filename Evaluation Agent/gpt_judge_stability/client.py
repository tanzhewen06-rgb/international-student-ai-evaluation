import importlib.util,re,json,hashlib
from pathlib import Path
from versions.v4_12.judgment import output_schema

# GPT judge.
MODEL='gpt-5.4-mini-2026-03-17'
CONFIG={'api':'openai.responses','reasoning_effort':'none','temperature':0,'max_output_tokens':4096,
        'output_format':'json_schema','strict_schema':False,'sdk_max_retries':0,'timeout_seconds':300}

MODEL_CONFIGS={MODEL:CONFIG,
    'gpt-6.1-sol':{**CONFIG,'reasoning_effort':'high','temperature':None,'max_output_tokens':32768}}

def model_layer(response_agent_dir):
    spec=importlib.util.spec_from_file_location('_gpt_judge_key_source',Path(response_agent_dir)/'models.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def check_credentials(response_agent_dir):
    model_layer(response_agent_dir)._get_api_key('openai')

def make_model(response_agent_dir,model_name=MODEL):
    if model_name not in MODEL_CONFIGS:raise ValueError('Select a configured GPT judge model.')
    config={**MODEL_CONFIGS[model_name],'adapter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    def call(model,prompt,instructions):
        if model!=model_name:raise ValueError('Judge model changed during the prepared trial.')
        count=re.findall(r'<checklist_output_count>([345])</checklist_output_count>',instructions)
        if len(count)!=1:raise ValueError('Missing original checklist count.')
        schema=output_schema(int(count[0]))
        from openai import OpenAI
        client=OpenAI(api_key=model_layer(response_agent_dir)._get_api_key('openai'),timeout=config['timeout_seconds'],max_retries=0)
        try:
            request=dict(model=model,input=prompt,instructions=instructions,
                reasoning={'effort':config['reasoning_effort']},max_output_tokens=config['max_output_tokens'],
                text={'format':{'type':'json_schema','name':'evaluation_v412','strict':False,'schema':schema}})
            if config['temperature'] is not None:request['temperature']=config['temperature']
            result=client.responses.create(**request)
            if getattr(result,'status',None)!='completed':raise RuntimeError('GPT response did not complete; no partial scores accepted.')
            if not getattr(result,'output_text',None):raise RuntimeError('GPT returned no grading JSON; inspect refusal or provider details.')
            raw=result.usage.model_dump() if getattr(result,'usage',None) is not None else {}
            output=raw.get('output_tokens');thinking=(raw.get('output_tokens_details') or {}).get('reasoning_tokens')
            usage={'input_tokens':raw.get('input_tokens'),'cached_input_tokens':(raw.get('input_tokens_details') or {}).get('cached_tokens'),
                   'output_tokens':output-thinking if type(output) is int and type(thinking) is int else None,
                   'thinking_tokens':thinking,'billable_output_tokens':output,'total_tokens':raw.get('total_tokens')}
            return {'text':result.output_text,'provider_status':result.status,'provider_model':getattr(result,'model',None),'usage':usage}
        finally:client.close()
    return call,config
