import logging
import json
from google import genai
from google.genai import types

def rewrite_resume(ranked_resume, job_requirements):
    client = genai.Client()
    job_req_str = json.dumps(job_requirements)
    
    # Determine job type for strategy adjustment
    job_type = job_requirements.get('job_type', 'technical').lower()
    
    system_prompt = f"""You are an ELITE resume writer whose SOLE MISSION is to achieve a 95-100% ATS keyword match rate. The candidate's career depends on passing this ATS filter.

STRATEGY BASED ON JOB TYPE: This is a "{job_type}" role.
{"- Reframe ALL technical/software experience into administrative, clerical, and customer-service language." if job_type == "administrative" else ""}
{"- Emphasize data entry, records management, customer service, policy adherence, teamwork, and communication." if job_type == "administrative" else ""}
{"- Technical jargon should be translated into business/admin terminology that ATS systems for admin roles will recognize." if job_type == "administrative" else ""}

MANDATORY RULES — FOLLOW ALL OF THEM:

1. **KEYWORD INJECTION IS YOUR #1 PRIORITY**: Every single keyword from the 'ats_critical_keywords' and 'exact_keyword_phrases' lists MUST appear VERBATIM in at least one bullet point. If a keyword doesn't naturally fit any bullet, FORCE it in by creatively reframing the bullet's context.

2. **CREATIVE REFRAMING IS REQUIRED**: You MUST aggressively reframe the candidate's experience to match the job. Examples:
   - "Used Git for version control" → "Maintained and updated records and documentation using a computerized information system"
   - "Built a React app" → "Developed and maintained a user-facing information system to deliver services to clients"
   - "Debugged code" → "Investigated and resolved system issues, applying problem-solving skills to provide solutions"
   - "Managed database schemas" → "Performed data entry, verification, and maintained student/client records in an information system"

3. **IMPLIED SKILL INJECTION**: If the job implies a skill (e.g., "fast-paced environment" implies "time management", "deadline management", "multitasking", "working under pressure"), you MUST weave those implied skills into the bullets even if the candidate didn't explicitly mention them. The candidate demonstrably has these skills — extract and surface them.

4. **EXACT PHRASE MATCHING**: Use the EXACT phrases from the job description — not synonyms, not paraphrases. If the job says "attention to detail", write "attention to detail" — NOT "detail-oriented". If the job says "work under pressure", write "work under pressure" — NOT "handle stress well".

5. **FORMAT**: Use 'Accomplished [Task] by [Action] using [Tool/Method], resulting in [Result/Impact]' structure for EVERY bullet. Start each with a strong action verb.

6. **QUANTITY & LENGTH**: Return exactly 3-4 bullets per experience entry and 2-3 bullets per project entry. CRITICAL: Each bullet MUST be concise—maximum 20 to 25 words per bullet. DO NOT write long, paragraph-like bullets. Short, impactful, and MUST BE KEYWORD DENSE.

7. **DO NOT REMOVE REAL ACCOMPLISHMENTS** — enhance them with job-relevant language. If a bullet mentions a real metric (40%, 80+, 90%), keep it.

8. **Return the EXACT same JSON structure provided**, replacing only the strings inside the 'bullets' arrays."""

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

    from utils import generate_content_with_fallback
    import time
    
    rewritten_resume = dict(ranked_resume)
    
    def rewrite_section(section_name, items):
        if not items:
            return items
            
        prompt = f"""
{system_prompt}

Job Requirements (USE THESE KEYWORDS):
{job_req_str}

Items to Rewrite ({section_name}):
{json.dumps(items, indent=2)}

CRITICAL REMINDER: Every keyword from 'ats_critical_keywords' and 'exact_keyword_phrases' MUST appear in your output. Count them. If any are missing, add them.

Respond ONLY with the rewritten JSON array containing the items exactly as structured above. Do not include markdown blocks like ```json.
"""
        try:
            logging.info(f"Rewriting {len(items)} {section_name} items in a batched API call...")
            time.sleep(1) # brief pause to prevent rate limiting
            response = generate_content_with_fallback(client, prompt, temperature=0.15)
            content = response.text.strip()
            if content.startswith('```json'):
                content = content[7:-3]
            elif content.startswith('```'):
                content = content[3:-3]
                
            rewritten_items = json.loads(content)
            return rewritten_items
        except Exception as e:
            logging.error(f"Failed to rewrite {section_name}: {e}")
            return items

    # Rewrite Experience
    if 'experience' in payload_to_rewrite and payload_to_rewrite['experience']:
        rewritten_exp = rewrite_section('experience', payload_to_rewrite['experience'])
        for i, exp in enumerate(rewritten_exp):
            if isinstance(exp, dict) and i < len(rewritten_resume.get('experience', [])):
                rewritten_resume['experience'][i]['bullets'] = exp.get('bullets', [])

    # Rewrite Projects
    if 'projects' in payload_to_rewrite and payload_to_rewrite['projects']:
        rewritten_proj = rewrite_section('projects', payload_to_rewrite['projects'])
        for i, proj in enumerate(rewritten_proj):
            if isinstance(proj, dict) and i < len(rewritten_resume.get('projects', [])):
                rewritten_resume['projects'][i]['bullets'] = proj.get('bullets', [])

    return rewritten_resume


def generate_professional_summary(resume_data, job_requirements):
    """Generates a tailored professional summary that mirrors the job description's key requirements."""
    client = genai.Client()
    job_req_str = json.dumps(job_requirements)
    
    job_title = job_requirements.get('job_title', 'the position')
    company_name = job_requirements.get('company_name', 'your organization')
    
    prompt = f"""You are an expert resume writer. Write a powerful 2-3 sentence professional summary for the TOP of a resume.

This summary MUST:
1. Mirror the job title and key qualifications EXACTLY as stated in the job description
2. Include at least 5 of the top ATS critical keywords from the job posting VERBATIM
3. Mention the candidate's education (Computing Science at Simon Fraser University, previously Computer Science at Langara College)
4. Mention years of relevant experience (3+ years customer service, data entry, and operational support)
5. Sound natural and confident, not keyword-stuffed
6. Be written in third person without using the candidate's name (e.g., "Detail-oriented Computing Science student with...")

Job Requirements:
{job_req_str}

Candidate Background:
- BSc Computing Science student at Simon Fraser University (GPA: 3.83)
- Associate of Science in Computer Science from Langara College (GPA: 4.09/4.33, Dean's Honour Roll)
- 3+ years as Work Associate at Real Canadian Superstore (customer service, data entry, cash handling, POS systems, training staff)
- Volunteer Full Stack Developer at Tomkulak Consortium (data management, information systems, team coordination)
- CompTIA Security+ certified

Return ONLY the summary text as a plain string. No JSON. No quotes. No markdown. Just the 2-3 sentences."""

    from utils import generate_content_with_fallback
    import time
    try:
        time.sleep(1)
        response = generate_content_with_fallback(client, prompt, temperature=0.2)
        summary = response.text.strip()
        # Clean any accidental quotes or markdown
        summary = summary.strip('"\'')
        if summary.startswith('```'):
            summary = summary.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        return summary
    except Exception as e:
        logging.error(f"Failed to generate professional summary: {e}")
        return ""


def tailor_skills(master_skills, job_requirements):
    """Dynamically selects and reorganizes skills to match the job description."""
    client = genai.Client()
    job_req_str = json.dumps(job_requirements)
    skills_str = json.dumps(master_skills)
    
    job_type = job_requirements.get('job_type', 'technical').lower()
    
    prompt = f"""You are an ATS optimization expert. Given the candidate's full skill set and the job requirements, create a TAILORED skills section that maximizes ATS match rate.

CANDIDATE'S TARGET DOMAINS: IT, Software Engineering, Data Analysis, and Cybersecurity internships.

RULES:
1. Select 4-5 skill categories that are MOST relevant to this "{job_type}" job
2. For technical/software roles, use categories like "Languages", "Frameworks & Libraries", "Databases", "Cloud & DevOps", "Cybersecurity", "Data Analysis", "Tools"
3. For admin roles, use categories like "Office & Computer Skills", "Communication & Interpersonal", "Technical Skills", "Administrative Skills"
4. INJECT keywords from the job description into the skills lists — every technology, tool, or skill mentioned in the job MUST appear
5. Remove skills that are clearly irrelevant to this specific job
6. Each category should have 5-10 skills
7. Prioritize EXACT keywords from the job posting
8. For software/IT internships, always include the candidate's programming languages and frameworks prominently

Candidate's Full Skills:
{skills_str}

Job Requirements:
{job_req_str}

Return a JSON object where keys are category names and values are arrays of skill strings.
Respond ONLY with valid JSON. No markdown."""

    from utils import generate_content_with_fallback
    import time
    try:
        time.sleep(1)
        response = generate_content_with_fallback(client, prompt, temperature=0.1)
        content = response.text.strip()
        if content.startswith('```json'):
            content = content[7:-3]
        elif content.startswith('```'):
            content = content[3:-3]
        tailored = json.loads(content)
        return tailored
    except Exception as e:
        logging.error(f"Failed to tailor skills: {e}")
        return master_skills


def tailor_certifications(certifications, job_requirements):
    """Rewrites certification bullet points to align with the job requirements."""
    client = genai.Client()
    job_req_str = json.dumps(job_requirements)
    certs_str = json.dumps(certifications)
    
    prompt = f"""You are an ATS resume expert. Rewrite the certification bullet points to emphasize aspects most relevant to this job.

Certifications:
{certs_str}

Job Requirements:
{job_req_str}

For each certification, provide EXACTLY 3 concise bullet points that highlight the most job-relevant aspects. Use keywords from the job description.

Return a JSON array with this structure:
[{{"name": "CompTIA Security+", "date": "Jan 2025", "bullets": ["Bullet 1 here", "Bullet 2 here", "Bullet 3 here"]}}]

Each bullet should be 10-20 words. Focus on job-relevant aspects.
Respond ONLY with valid JSON. No markdown."""

    from utils import generate_content_with_fallback
    import time
    try:
        time.sleep(1)
        response = generate_content_with_fallback(client, prompt, temperature=0.1)
        content = response.text.strip()
        if content.startswith('```json'):
            content = content[7:-3]
        elif content.startswith('```'):
            content = content[3:-3]
        return json.loads(content)
    except Exception as e:
        logging.error(f"Failed to tailor certifications: {e}")
        # Return original details as bullets
        return [{"name": c.get("name", ""), "date": c.get("date", ""), "bullets": c.get("details", [])} for c in certifications]

