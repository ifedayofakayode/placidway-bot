import json
import re

from openai import OpenAI

import config

_client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)


def chat_json(system, user):
    resp = _client.chat.completions.create(
        model=config.LLM_MODEL,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        timeout=40,        
    )
    text = resp.choices[0].message.content
    return json.loads(re.search(r"\{.*\}", text, re.S).group(0))