import json
import logging
from google import genai
from google.genai import types

def parse_job_description(job_text):
    """Parses a raw job description into structured requirements."""
    client = genai.Client()
    
    prompt = f"""
You are an expert technical recruiter. Parse the following job description into a structured JSON object.
Extract the required skills, technologies, and key responsibilities.
Respond ONLY with valid JSON.

Job Description:
{job_text}

JSON Format:
{{
    "company_name": "Short, single-word name of the Company (infer from context like location or email if not explicitly stated, or empty string if totally unknown)",
    "skills": ["skill1", "skill2"],
    "technologies": ["tech1", "tech2"],
    "responsibilities": ["resp1", "resp2"]
}}
"""
    from utils import generate_content_with_fallback
    try:
        response = generate_content_with_fallback(client, prompt, temperature=0.0)
        content = response.text.strip()
        # Clean up markdown if present
        if content.startswith('```json'):
            content = content[7:-3]
        elif content.startswith('```'):
            content = content[3:-3]
        return json.loads(content)
    except Exception as e:
        logging.error(f"Failed to parse job description: {e}")
        return {}
