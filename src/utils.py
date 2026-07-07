"""
Utility functions for file IO, environment management, and resilient Gemini API interactions.
This module provides common helper methods shared across the resume builder pipeline.
"""
import os
import json

def load_env(filepath=".env"):
    """
    Parses a local .env file and sets environment variables in os.environ.
    
    Args:
        filepath (str): Path to the .env file. Defaults to ".env".
    """
    if not os.path.exists(filepath):
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Ignore blank lines and comments
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

def read_file(filepath):
    """
    Reads the content of a text file.
    
    Args:
        filepath (str): Absolute or relative path to the target text file.
        
    Returns:
        str: The raw text content of the file.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(filepath, content):
    """
    Writes text content to a file, overwriting existing content.
    
    Args:
        filepath (str): Target path where the file will be saved.
        content (str): Text string to write into the file.
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def read_json(filepath):
    """
    Reads and parses a JSON file into a Python dictionary or list.
    
    Args:
        filepath (str): Path to the JSON file.
        
    Returns:
        dict | list: Parsed Python data structure from JSON.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_json(filepath, data):
    """
    Serializes Python data to a formatted JSON file with 4-space indentation.
    
    Args:
        filepath (str): Target file path.
        data (dict | list): Python data structure to serialize.
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def generate_content_with_fallback(client, prompt, temperature=0.1):
    """
    Executes a Gemini generation request with automatic fallback across multiple model tiers.
    If rate limits (429), quota exhaustion, or 404 errors occur, it automatically cascades to next available models.
    
    Args:
        client (google.genai.Client): Initialized Google GenAI SDK client.
        prompt (str): Prompt text to send to the AI model.
        temperature (float): Sampling temperature (default 0.1 for deterministic ATS optimization).
        
    Returns:
        google.genai.types.GenerateContentResponse: The API response object containing generated text.
        
    Raises:
        Exception: If all fallback models in the tier list fail.
    """
    import logging
    from google.genai import types
    
    # Priority cascade order: prefer latest 3.5/3 Flash models, falling back to 2.5 and Lite tiers
    models = [
        'gemini-3.5-flash',
        'gemini-3-flash-preview',
        'gemini-2.5-flash',
        'gemini-3.1-flash-lite',
        'gemini-2.5-flash-lite'
    ]
    
    last_error = None
    for model_name in models:
        try:
            logging.info(f"   -> Calling AI Agent ({model_name})...")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    # Enable small thinking budget for Gemini 3 models to enhance reasoning accuracy
                    thinking_config=types.ThinkingConfig(thinking_budget=1024) if "gemini-3" in model_name else None
                )
            )
            return response
        except Exception as e:
            error_message = str(e).lower()
            last_error = e
            # Catch rate limit (429), quota exhaustion, model not found (404/400), or API availability errors
            if any(err in error_message for err in ['429', 'quota', 'exhausted', 'not found', '404', '400', '503']):
                logging.info(f"   -> Model {model_name} busy/limit reached. Trying next AI model...")
                continue
            else:
                logging.error(f"Unexpected error with {model_name}: {e}. Trying next model anyway...")
                continue
                
    logging.error("All preferred models exhausted their limits or failed.")
    raise Exception(f"All models failed. Last error: {last_error}")
