import json
from openai import OpenAI

API_KEY = None
BASE_URL = 'https://api.openai.com/v1'
CLIENT = None

def configure(api_key: str, base_url: str):
    global API_KEY, BASE_URL, CLIENT
    API_KEY = api_key
    BASE_URL = base_url.rstrip('/')
    CLIENT = OpenAI(api_key=API_KEY, base_url=BASE_URL)

def chat(system: str, user: str, max_tokens: int = 512):
    if CLIENT is None:
        return None
    try:
        r = CLIENT.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role':'system','content':system},
                {'role':'user','content':user}
            ],
            max_tokens=max_tokens,
            temperature=0.2
        )
        return r.choices[0].message.content
    except Exception:
        return None

def json_response(system: str, user: str, schema_hint: str):
    content = chat(system, user + "\n" + schema_hint, max_tokens=800)
    if not content:
        return None
    try:
        return json.loads(content)
    except Exception:
        try:
            start = content.find('{')
            end = content.rfind('}')
            if start >= 0 and end >= 0:
                return json.loads(content[start:end+1])
        except Exception:
            return None
    return None
