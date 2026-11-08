"""Provider adapters for the unchanged V4.8 grading protocol."""
import os
from versions.v4_8.judgment import output_schema

def _usage(data):
    if hasattr(data,'model_dump'):return data.model_dump()
    if hasattr(data,'to_dict'):return data.to_dict()
    return data if isinstance(data,dict) else {}

def deepseek_key():
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        from keyring.backends.Windows import WinVaultKeyring
        key=WinVaultKeyring().get_password('AI Persona Analysis','DEEPSEEK_API_KEY')
    if not key:raise RuntimeError('No saved DEEPSEEK_API_KEY in environment or Windows Credential Manager.')
    return key

def check_credentials(response_agent_dir,models):
    from runtime.models import load_model_layer
    import importlib.util
    spec=importlib.util.spec_from_file_location('_credential_preflight',response_agent_dir/'models.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for name in models:
        load_model_layer(response_agent_dir,name,compact='V4.8')
        if name.startswith('deepseek-'):deepseek_key()
        elif name.startswith('gemini-'):module._get_api_key('gemini')
        else:raise ValueError('Select a tested judge provider.')

def make_model(module,model_name):
    if model_name.startswith('deepseek-'):
        config={'base_url':'https://api.deepseek.com','reasoning_effort':'none','max_output_tokens':4096,'output_format':'json_schema','sdk_max_retries':0}
    else:
        config=dict(module.GENERATION_CONFIGS.get(model_name,{}));config['max_output_tokens']=4096
    def call(model,prompt,instructions):
        if model!=model_name:raise ValueError('Judge model changed during a prepared run.')
        if model.startswith('gemini-'):
            from google import genai
            client=genai.Client(api_key=module._get_api_key('gemini'))
            try:
                result=client.interactions.create(model=model,input=prompt,system_instruction=instructions,
                    generation_config=config,response_format={'type':'text','mime_type':'application/json','schema':output_schema()},timeout=300)
                raw=_usage(getattr(result,'usage',None))
                usage={k:raw.get(field) for k,field in [('input_tokens','total_input_tokens'),('cached_input_tokens','total_cached_tokens'),('output_tokens','total_output_tokens'),('thinking_tokens','total_thought_tokens'),('total_tokens','total_tokens')]}
                out=usage['output_tokens'];thought=usage['thinking_tokens']
                usage['billable_output_tokens']=out+thought if type(out) is int and type(thought) is int else None
                return {'text':result.output_text,'provider_status':getattr(result,'status',None),'provider_model':getattr(result,'model',None),'usage':usage}
            finally:client.close()
        if model.startswith('deepseek-'):
            from openai import OpenAI
            client=OpenAI(api_key=deepseek_key(),base_url=config['base_url'],timeout=300,max_retries=0)
            try:
                result=client.responses.create(model=model,input=prompt,instructions=instructions,
                    reasoning={'effort':config['reasoning_effort']},max_output_tokens=config['max_output_tokens'],
                    text={'format':{'type':'json_schema','name':'evaluation_v48','schema':output_schema()}})
                raw=_usage(getattr(result,'usage',None));output=raw.get('output_tokens')
                thinking=(raw.get('output_tokens_details') or {}).get('reasoning_tokens')
                usage={'input_tokens':raw.get('input_tokens'),'cached_input_tokens':(raw.get('input_tokens_details') or {}).get('cached_tokens'),
                    'output_tokens':output-thinking if type(output) is int and type(thinking) is int else None,
                    'thinking_tokens':thinking,'billable_output_tokens':output,'total_tokens':raw.get('total_tokens')}
                return {'text':result.output_text,'provider_status':getattr(result,'status',None),'provider_model':getattr(result,'model',None),'usage':usage}
            finally:client.close()
        raise ValueError('Use a tested Gemini or DeepSeek judge adapter.')
    return call,config
