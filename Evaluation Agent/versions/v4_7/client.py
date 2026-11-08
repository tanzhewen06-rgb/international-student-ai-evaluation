"""Evaluation-only structured output and usage; reuse saved Response Agent credentials."""
from versions.v4_7.judgment import output_schema

def _usage(data):
    if hasattr(data,'model_dump'):return data.model_dump()
    if hasattr(data,'to_dict'):return data.to_dict()
    return data if isinstance(data,dict) else {}

def make_model(module,model_name):
    config=dict(module.GENERATION_CONFIGS.get(model_name,{}))
    config['max_output_tokens']=4096
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
                return {'text':result.output_text,'provider_status':getattr(result,'status',None),'usage':usage}
            finally:client.close()
        raise ValueError('V4.7 structured usage adapter is configured for the existing Gemini judge; select a tested adapter before changing provider.')
    return call,config
