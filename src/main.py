"""
Main Pipeline Orchestrator for AI Resume Builder.
Coordinates job description parsing, semantic bullet ranking, aggressive ATS rewriting,
dynamic skills tailoring, professional summary synthesis, and LaTeX compilation.
"""
import sys
import os
import json
import logging
import warnings

# Suppress SDK warnings regarding non-text response parts (like thinking_signature)
warnings.filterwarnings("ignore", message=".*there are non-text parts in the response.*")

from utils import load_env, read_file, read_json, write_file
from parse_job import parse_job_description
from rank import rank_bullets
from rewrite import rewrite_resume, generate_professional_summary, tailor_skills, tailor_certifications
from latex_gen import generate_latex, compile_latex

# Configure application-level logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    """
    Main entry point for executing the end-to-end resume tailoring workflow.
    Expects path to job description file as command-line argument.
    """
    if len(sys.argv) < 2:
        print("Usage: python main.py <job.txt>")
        sys.exit(1)
        
    job_file = sys.argv[1]
    if not os.path.exists(job_file):
        logging.error(f"Job file not found: {job_file}")
        sys.exit(1)
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(base_dir, '.env')
    load_env(env_path)
    
    if not os.getenv("GEMINI_API_KEY"):
        logging.error("GEMINI_API_KEY not found in .env or environment variables.")
        sys.exit(1)
        
    # Paths
    master_resume_path = os.path.join(base_dir, 'data', 'master_resume.json')
    template_path = os.path.join(base_dir, 'data', 'template.tex')
    output_dir = os.path.join(base_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    # Check user preference
    print("\nWhat would you like to generate?")
    print("1: Resume only")
    print("2: Resume + Cover Letter")
    choice = input("Enter option (1 or 2): ").strip()
    generate_cl = (choice == "2")
    
    # 1. Parse Job Description (Enhanced — now extracts soft skills, ATS keywords, job type, etc.)
    logging.info("Parsing job description (enhanced ATS extraction)...")
    job_text = read_file(job_file)
    job_reqs = parse_job_description(job_text)
    job_req_text = json.dumps(job_reqs)
    
    job_type = job_reqs.get('job_type', 'unknown')
    job_title = job_reqs.get('job_title', 'Unknown Position')
    logging.info(f"Detected job type: {job_type} | Title: {job_title}")
    logging.info(f"Found {len(job_reqs.get('ats_critical_keywords', []))} ATS critical keywords")
    
    # 2. Read Master Resume
    logging.info("Loading master resume...")
    master_resume = read_json(master_resume_path)
    
    # 3. Rank Bullets (semantic similarity)
    logging.info("Ranking bullets via semantic similarity...")
    ranked_resume = rank_bullets(master_resume, job_req_text)
    
    # 4. Rewrite Bullets (aggressive ATS optimization)
    logging.info("Rewriting bullets for MAXIMUM ATS alignment...")
    tailored_resume = rewrite_resume(ranked_resume, job_reqs)
    
    # 5. Tailor Skills Section (dynamic — adapts categories to job type)
    logging.info("Tailoring skills section to job requirements...")
    tailored_skills = tailor_skills(master_resume.get('technical_skills', {}), job_reqs)
    tailored_resume['technical_skills'] = tailored_skills
    
    # 6. Generate Professional Summary
    logging.info("Generating tailored professional summary...")
    summary_text = generate_professional_summary(tailored_resume, job_reqs)
    
    # 7. Tailor Certifications
    logging.info("Tailoring certifications to job requirements...")
    tailored_certs = tailor_certifications(master_resume.get('certifications', []), job_reqs)
    
    # 8. Generate LaTeX (with all new sections)
    logging.info("Generating Resume LaTeX...")
    template_content = read_file(template_path)
    latex_content = generate_latex(tailored_resume, template_content, summary_text, tailored_certs)
    
    company_name = job_reqs.get('company_name', '').strip()
    short_company_name = ""
    if company_name:
        clean_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-')).strip()
        short_company_name = clean_company_name.split()[0] if clean_company_name else ""
        
    if short_company_name:
        file_name = f'resume {short_company_name}.tex'
    else:
        file_name = 'resume.tex'
        
    tex_out_path = os.path.join(output_dir, file_name)
    write_file(tex_out_path, latex_content)
    
    # 9. Compile Resume PDF
    logging.info("Compiling Resume PDF...")
    compile_latex(tex_out_path, output_dir)
    pdf_file = file_name.replace('.tex', '.pdf')
    logging.info(f"Resume Done! Check {output_dir}/{pdf_file}")

    # 10. Generate Cover Letter if requested
    if generate_cl:
        from cover_letter import generate_cover_letter_data
        from latex_gen import generate_cover_letter_latex
        
        cl_template_path = os.path.join(base_dir, 'data', 'cover_letter_template.tex')
        cl_template_content = read_file(cl_template_path)
        
        logging.info("Generating Cover Letter Content...")
        cl_data = generate_cover_letter_data(tailored_resume, job_reqs)
        
        logging.info("Generating Cover Letter LaTeX...")
        cl_latex_content = generate_cover_letter_latex(cl_data, cl_template_content)
        
        if short_company_name:
            cl_file_name = f'cover_letter {short_company_name}.tex'
        else:
            cl_file_name = 'cover_letter.tex'
            
        cl_tex_out_path = os.path.join(output_dir, cl_file_name)
        write_file(cl_tex_out_path, cl_latex_content)
        
        logging.info("Compiling Cover Letter PDF...")
        compile_latex(cl_tex_out_path, output_dir)
        cl_pdf_file = cl_file_name.replace('.tex', '.pdf')
        logging.info(f"Cover Letter Done! Check {output_dir}/{cl_pdf_file}")

if __name__ == "__main__":
    main()
