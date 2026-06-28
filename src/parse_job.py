import json
import logging
from google import genai
from google.genai import types

def parse_job_description(job_text):
    """Parses a raw job description into comprehensive structured requirements for ATS optimization."""
    client = genai.Client()
    
    prompt = f"""
You are an expert ATS (Applicant Tracking System) analyst and technical recruiter. Your job is to deeply analyze this job description and extract EVERYTHING an ATS would scan for.

CRITICAL: Be exhaustive. Miss nothing. The candidate's interview depends on this.

Job Description:
{job_text}

Return a JSON object with these EXACT keys:

{{
    "company_name": "Short, commonly used name of the company (e.g., 'Langara College' not 'Langara College Vancouver Campus')",
    "job_title": "The exact job title as written in the posting",
    "job_type": "One of: 'technical', 'administrative', 'hybrid' — based on whether the role is primarily software/engineering, clerical/admin/customer-service, or a mix",
    "skills": ["Every hard skill mentioned — software, tools, systems, technical abilities"],
    "soft_skills": ["Every soft skill mentioned or implied — communication, teamwork, attention to detail, etc."],
    "technologies": ["Specific software, systems, or tools mentioned (e.g., Banner, Excel, Word, PowerPoint)"],
    "responsibilities": ["Key duties and responsibilities listed"],
    "required_education": "The minimum education requirement as stated",
    "required_experience": "The experience requirement as stated (years, type)",
    "ats_critical_keywords": ["The TOP 20 most important keywords/phrases an ATS would scan for in this specific posting. Include EXACT multi-word phrases as they appear in the job description. These should be the words that if missing from a resume, would cause automatic rejection."],
    "exact_keyword_phrases": ["Every significant multi-word phrase from the posting that should appear VERBATIM on the resume — e.g., 'attention to detail', 'work under pressure', 'customer service', 'data entry', 'student information system', etc."],
    "implied_skills": ["Skills that are NOT explicitly stated but are LOGICALLY IMPLIED by the duties — e.g., if job says 'manage high volume', that implies 'time management', 'deadline management', 'prioritization'. If job says 'fast-paced', that implies 'working under pressure', 'multitasking'. Think about what skills someone MUST have to do this job well."]
}}

Be thorough. Include duplicates if a keyword appears in multiple categories — redundancy is fine.
Respond ONLY with valid JSON. No markdown formatting.
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
