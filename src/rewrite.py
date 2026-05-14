import logging
import json
from google import genai
from google.genai import types

def rewrite_resume(ranked_resume, job_requirements):
    client = genai.Client()
    job_req_str = json.dumps(job_requirements)
    
    system_prompt = """You are an expert resume writer. Your task is to rewrite the candidate's resume bullets to better align with the job requirements.
CRITICAL RULES:
1. DO NOT fabricate or invent any experience, skills, or metrics.
2. ONLY rewrite and reorder existing content to emphasize relevance to the job.
3. Maintain factual accuracy at all times.
4. Keep output concise and highly ATS-friendly. Naturally integrate important keywords from the job requirements.
5. Format EVERY bullet point using the 'Task, Tool, Result' structure (e.g., 'Accomplished [Task] by doing [Action] using [Tools/Technologies], resulting in [Result/Metrics]').
6. Start each bullet point with a strong action verb. Focus on impact and business value.
7. If a bullet cannot be tailored to the job without lying, keep its original meaning but still reformat it to the 'Task, Tool, Result' structure.
8. Return the EXACT same JSON structure provided, replacing only the strings inside the 'bullets' arrays."""

    # Extract just the parts that need rewriting to minimize output tokens
    payload_to_rewrite = {}
    
    if 'experience' in ranked_resume:
        payload_to_rewrite['experience'] = []
        for exp in ranked_resume['experience']:
            payload_to_rewrite['experience'].append({
                'title': exp.get('title'),
                'company': exp.get('company'),
                'bullets': exp.get('bullets', [])
            })
            
    if 'projects' in ranked_resume:
        payload_to_rewrite['projects'] = []
        for proj in ranked_resume['projects']:
            payload_to_rewrite['projects'].append({
                'name': proj.get('name'),
                'type': proj.get('type'),
                'bullets': proj.get('bullets', [])
            })

    if not payload_to_rewrite:
        return ranked_resume

    prompt = f"""
{system_prompt}

Job Requirements:
{job_req_str}

Items to Rewrite:
{json.dumps(payload_to_rewrite, indent=2)}

Respond ONLY with the rewritten JSON object matching the exact structure above. Do not include markdown blocks like ```json.
"""
    
    from utils import generate_content_with_fallback
    import time
    
    rewritten_resume = dict(ranked_resume)
    
    try:
        logging.info("Rewriting all bullets in a single optimized API call...")
        response = generate_content_with_fallback(client, prompt, temperature=0.1)
        content = response.text.strip()
        if content.startswith('```json'):
            content = content[7:-3]
        elif content.startswith('```'):
            content = content[3:-3]
            
        rewritten_payload = json.loads(content)
        
        # Merge back into the original resume structure
        if 'experience' in rewritten_payload:
            for i, exp in enumerate(rewritten_payload['experience']):
                if i < len(rewritten_resume.get('experience', [])):
                    rewritten_resume['experience'][i]['bullets'] = exp.get('bullets', [])
                    
        if 'projects' in rewritten_payload:
            for i, proj in enumerate(rewritten_payload['projects']):
                if i < len(rewritten_resume.get('projects', [])):
                    rewritten_resume['projects'][i]['bullets'] = proj.get('bullets', [])
                    
    except Exception as e:
        logging.error(f"Failed to rewrite bullets: {e}")
        return ranked_resume

    return rewritten_resume
