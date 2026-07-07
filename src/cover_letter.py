"""
Cover Letter Generation Module.
Leverages Google Gemini LLM to synthesize candidate resume qualifications and job description requirements
into a structured, personalized cover letter formatted for LaTeX rendering.
"""
import json
import logging
from google import genai
from google.genai import types
from datetime import datetime

def generate_cover_letter_data(resume_data, job_requirements):
    """
    Generates tailored cover letter data based on the candidate's resume and target job description.
    
    Args:
        resume_data (dict): Candidate's full resume dictionary.
        job_requirements (dict): Extracted ATS requirements dictionary from parse_job_description.
        
    Returns:
        dict | None: Structured cover letter dictionary matching LaTeX template placeholders,
                     or None if generation or JSON parsing fails.
    """
    client = genai.Client()
    job_req_str = json.dumps(job_requirements)
    resume_str = json.dumps(resume_data)
    current_date = datetime.now().strftime("%B %d, %Y")
    
    prompt = f"""
You are an expert career coach and cover letter writer.
Write a highly compelling, professional, and tailored cover letter based on the candidate's resume and the job requirements.
The output MUST be a valid JSON object matching exactly these keys:
- DATE: The current date (use '{current_date}')
- HIRING_MANAGER_NAME: Infer from the job description or use 'Hiring Manager'
- COMPANY_NAME: The company name from the job description
- COMPANY_ADDRESS: The company's street address (infer from job description or use a generic 'Company Address' if not available)
- COMPANY_CITY_PROVINCE: The company's city and province/state (infer from job description or use 'City, Province' if not available)
- JOB_TITLE: The exact job title being applied for
- SALUTATION: E.g., 'Hiring Manager' or the actual name if known
- OPENING_PARAGRAPH: Express genuine interest in the company's mission/values and connect to the specific role.
- TECHNICAL_PARAGRAPH: Highlight the most relevant project or technical experience from the resume with specific metrics and tech stack.
- SUPPORTING_PARAGRAPH: Reinforce with additional experiences (DSA, cloud, part-time work, etc.) that show adaptability.
- CLOSING_PARAGRAPH: Express enthusiasm, mention availability, and thank the reader.

Job Requirements:
{job_req_str}

Candidate Resume:
{resume_str}

Respond ONLY with valid JSON. Do not include markdown formatting or any other text.
"""
    from utils import generate_content_with_fallback
    try:
        logging.info("   -> Generating cover letter content via Gemini API...")
        # Use temperature 0.3 for a balance of creativity and professional tone
        response = generate_content_with_fallback(client, prompt, temperature=0.3)
        content = response.text.strip()
        # Strip markdown code block fences if returned by the LLM
        if content.startswith('```json'):
            content = content[7:-3]
        elif content.startswith('```'):
            content = content[3:-3]
            
        return json.loads(content)
    except Exception as e:
        logging.error(f"Failed to generate cover letter data: {e}")
        return None
