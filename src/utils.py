import os
import json

def load_env(filepath=".env"):
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

def read_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def read_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def generate_content_with_fallback(client, prompt, temperature=0.1):
    import logging
    from google.genai import types
    
    models = [
        'gemini-3.0-flash',
        'gemini-3-flash',
        'gemini-2.5-flash',
        'gemini-3.1-flash-lite',
        'gemini-2.5-flash-lite'
    ]
    
    last_error = None
    for model_name in models:
        try:
            logging.info(f"Attempting API call with preferred model: {model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature
                )
            )
            return response
        except Exception as e:
            error_message = str(e).lower()
            last_error = e
            # Catch rate limit, quota, model not found, or bad request (if name is slightly off)
            if any(err in error_message for err in ['429', 'quota', 'exhausted', 'not found', '404', '400']):
                logging.warning(f"Model {model_name} unavailable (limit/not found). Trying next in preference list...")
                continue
            else:
                logging.error(f"Unexpected error with {model_name}: {e}. Trying next model anyway...")
                continue
                
    logging.error("All preferred models exhausted their limits or failed.")
    raise Exception(f"All models failed. Last error: {last_error}")
