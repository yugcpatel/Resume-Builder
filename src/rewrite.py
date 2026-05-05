import logging
import json
from google import genai
from google.genai import types

def rewrite_resume(ranked_resume, job_requirements):
    client = genai.Client()
    job_req_str = json.dumps(job_requirements)
    
    rewritten_resume = dict(ranked_resume)
    
    system_prompt = """You are an expert resume writer. Your task is to rewrite the candidate's resume bullets to better align with the job requirements.
CRITICAL RULES:
1. DO NOT fabricate or invent any experience, skills, or metrics.
2. ONLY rewrite and reorder existing content to emphasize relevance to the job.
3. Maintain factual accuracy at all times.
4. Keep output concise and ATS-friendly.
5. If a bullet cannot be tailored without lying, keep it as is.
6. Return the exact same JSON structure provided for the bullets list."""

    def rewrite_bullets_for_item(item_title, item_context, bullets):
        if not bullets:
            return bullets
            
        prompt = f"""
{system_prompt}

Job Requirements:
{job_req_str}

Context: {item_title} ({item_context})
Current Bullets:
{json.dumps(bullets)}

Rewrite these bullets to better match the job requirements following the CRITICAL RULES.
Return a valid JSON list of strings. Do not include any markdown blocks, just the JSON array.
"""
        import time
        try:
            logging.info(f"Waiting 13 seconds to respect API rate limits (5 RPM)...")
            time.sleep(13)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1
                )
            )
            content = response.text.strip()
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
                
            rewritten_bullets = json.loads(content)
            if isinstance(rewritten_bullets, list):
                return rewritten_bullets
        except Exception as e:
            logging.error(f"Failed to rewrite bullets for {item_title}: {e}")
        return bullets

    # Rewrite Experience
    if 'experience' in ranked_resume:
        for i, exp in enumerate(ranked_resume.get('experience', [])):
            bullets = exp.get('bullets', [])
            new_bullets = rewrite_bullets_for_item(exp.get('title'), exp.get('company'), bullets)
            rewritten_resume['experience'][i]['bullets'] = new_bullets

    # Rewrite Projects
    if 'projects' in ranked_resume:
        for i, proj in enumerate(ranked_resume.get('projects', [])):
            bullets = proj.get('bullets', [])
            new_bullets = rewrite_bullets_for_item(proj.get('name'), proj.get('type'), bullets)
            rewritten_resume['projects'][i]['bullets'] = new_bullets

    return rewritten_resume
