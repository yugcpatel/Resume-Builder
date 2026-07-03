"""
Resume Rewriting and ATS Optimization Module.
Orchestrates LLM prompts to rewrite bullet points, synthesize tailored summaries,
and restructure skills and certification sections with strict character constraints and zero keyword repetition.
"""
import logging
import json
from google import genai
from google.genai import types

def rewrite_resume(ranked_resume, job_requirements):
    """
    Rewrites candidate experience and project bullet points to maximize ATS keyword alignment
    while strictly enforcing vocabulary diversity across sections (no repeated wording).
    
    Args:
        ranked_resume (dict): Filtered resume dictionary from semantic ranking.
        job_requirements (dict): Extracted ATS requirements dictionary from parse_job_description.
        
    Returns:
        dict: Updated resume dictionary with rewritten, ATS-optimized bullet points.
    """
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

8. **Return the EXACT same JSON structure provided**, replacing only the strings inside the 'bullets' arrays.

9. **ZERO REPETITION / VOCABULARY DIVERSITY ACROSS EXPERIENCE AND PROJECTS**: DO NOT repeat the same action verbs, nouns, ATS keywords, or phrasing across multiple bullet points. Once a keyword, tool, or phrase has been used in one bullet point, DO NOT repeat it in another bullet point or section! Use diverse vocabulary and distinct angles for every single bullet point so each item reads uniquely without repetitive wording."""

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
    
    def rewrite_section(section_name, items, previous_context=""):
        if not items:
            return items
            
        anti_rep_prompt = ""
        if previous_context:
            anti_rep_prompt = f"""
CRITICAL ANTI-REPETITION INSTRUCTION FOR {section_name.upper()}:
The following bullet points and phrasing were ALREADY generated in the Experience section:
{previous_context}

YOU MUST NOT REPEAT OR RECYCLE ANY OF THE SAME KEYWORDS, PHRASES, ACTION VERBS, OR SENTENCE STRUCTURES USED ABOVE! 
For {section_name}, you MUST use completely different vocabulary, different action verbs, and different ATS keywords from the job requirements that were not already covered in Experience. Ensure 100% unique phrasing across the entire resume.
"""

        prompt = f"""
{system_prompt}

Job Requirements (USE THESE KEYWORDS):
{job_req_str}

Items to Rewrite ({section_name}):
{json.dumps(items, indent=2)}
{anti_rep_prompt}
CRITICAL REMINDER: Weave in relevant ATS keywords naturally across the resume, but STRICTLY FORBID any repetition of phrasing, action verbs, or keyword strings between bullet points or between Experience and Projects. Every single bullet point must be 100% unique in wording and structure. YOU MUST USE ALL THE KEY WORDS DO NOT COMPROMISE ON KEYWORDS FOR ANTI REPETITION .

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
    already_used_text = ""
    if 'experience' in payload_to_rewrite and payload_to_rewrite['experience']:
        rewritten_exp = rewrite_section('experience', payload_to_rewrite['experience'])
        for i, exp in enumerate(rewritten_exp):
            if isinstance(exp, dict) and i < len(rewritten_resume.get('experience', [])):
                bullets = exp.get('bullets', [])
                rewritten_resume['experience'][i]['bullets'] = bullets
                already_used_text += f"\n- {exp.get('title', '')} at {exp.get('company', '')}: " + " | ".join(bullets)

    # Rewrite Projects
    if 'projects' in payload_to_rewrite and payload_to_rewrite['projects']:
        rewritten_proj = rewrite_section('projects', payload_to_rewrite['projects'], previous_context=already_used_text)
        for i, proj in enumerate(rewritten_proj):
            if isinstance(proj, dict) and i < len(rewritten_resume.get('projects', [])):
                rewritten_resume['projects'][i]['bullets'] = proj.get('bullets', [])

    return rewritten_resume


def generate_professional_summary(resume_data, job_requirements):
    """
    Generates a powerful 2-3 sentence professional summary tailored to the target job title
    and ATS critical keywords, written in the third person without using candidate names.
    
    Args:
        resume_data (dict): Candidate master resume dictionary.
        job_requirements (dict): Extracted ATS requirements dictionary.
        
    Returns:
        str: Clean 2-3 sentence summary string ready for LaTeX injection.
    """
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
    """
    Dynamically selects and formats skills into exactly 5 categories, strictly enforcing character lengths
    so categories 1-3 render to 3 lines and categories 4-5 render to 2 lines in LaTeX.
    
    Args:
        master_skills (dict): Master skills dictionary grouped by general category.
        job_requirements (dict): Extracted ATS requirements dictionary.
        
    Returns:
        dict: Tailored dictionary containing exactly 5 categories ordered by importance.
    """
    client = genai.Client()
    job_req_str = json.dumps(job_requirements)
    skills_str = json.dumps(master_skills)
    
    job_type = job_requirements.get('job_type', 'technical').lower()
    
    prompt = f"""You are an ATS optimization expert. Given the candidate's full skill set and the job requirements, create a TAILORED skills section that maximizes ATS match rate.

CANDIDATE'S TARGET DOMAINS: IT, Software Engineering, Data Analysis, and Cybersecurity internships.

RULES:
1. Select EXACTLY 5 skill categories that are MOST relevant to this "{job_type}" job. You MUST output exactly 5 categories—no more, no less! Order them by importance from most important (1st) to least important (5th).
2. For technical/software roles, use comprehensive category names like "Programming Languages & Core CS", "Cloud, DevOps & Architecture", "Embedded Systems & Low-Level Programming", "Databases & Data Management", "Frameworks, AI & Development Tools".
3. For admin/business roles, use categories like "Office & Computer Skills", "Data Analytics & Reporting", "Communication & Interpersonal", "Digital Transformation & AI", "Project & Stakeholder Management".
4. INJECT keywords from the job description into the skills lists — EVERY single technology, tool, methodology, or skill mentioned in the job MUST appear verbatim! Do not compromise on ATS keyword coverage!
5. Remove skills that are clearly irrelevant to this specific job.
6. CRITICAL FORMATTING REQUIREMENT FOR STRICT 2-PAGE LAYOUT (3 LINES FOR CATEGORIES 1-3, 2 LINES FOR CATEGORIES 4-5):
   - You MUST format the 5 categories with precise character lengths so they render to exact line counts in LaTeX:
   - Categories 1, 2, and 3 MUST each fill EXACTLY 3 lines in LaTeX! In our small font, this requires the string (Category Name + ": " + comma-separated skills) to have a total character length strictly between 210 and 260 characters (around 12 to 16 distinct skills/technologies per category).
   - Categories 4 and 5 MUST each fill EXACTLY 2 lines in LaTeX! This requires the string (Category Name + ": " + comma-separated skills) to have a total character length strictly between 135 and 170 characters (around 7 to 10 distinct skills/technologies per category).
   - Do not generate short 1-line categories or overly long 4-line categories! Strictly adhere to 3 lines for the first 3 categories, and 2 lines for the last 2 categories.
7. Prioritize EXACT keywords from the job posting.
8. For software/IT internships, always include the candidate's programming languages, frameworks, cloud tools, databases, and core CS fundamentals prominently.
9. Keep individual skill entries clean and readable (e.g., "Amazon Web Services (AWS)", "Data Structure Implementation", "CI/CD Pipelines (GitHub Actions, Jenkins)"). Group related concepts when helpful to maximize keyword density without cluttering.

Candidate's Full Skills:
{skills_str}

Job Requirements:
{job_req_str}

Return a JSON object where keys are category names and values are arrays of skill strings (e.g., {{"Programming": ["Python", "Java", "SQL"]}}). Do not include the category name inside the array.
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
        if isinstance(tailored, dict) and len(tailored) > 5:
            tailored = dict(list(tailored.items())[:5])
        return tailored
    except Exception as e:
        logging.error(f"Failed to tailor skills: {e}")
        return master_skills


def tailor_certifications(certifications, job_requirements):
    """
    Rewrites certification details into exactly 3 concise, job-relevant bullet points per certification.
    
    Args:
        certifications (list[dict]): List of candidate certification dictionaries.
        job_requirements (dict): Extracted ATS requirements dictionary.
        
    Returns:
        list[dict]: List of tailored certification dictionaries with formatted bullet points.
    """
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

