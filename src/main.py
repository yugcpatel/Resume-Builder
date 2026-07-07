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

# Create a filter to strip out noisy SDK / HTTP logs and formatting
class CleanLogFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        noisy_phrases = [
            "HTTP Request:",
            "AFC is enabled",
            "there are non-text parts in the response",
            "non-text parts"
        ]
        return not any(phrase in msg for phrase in noisy_phrases)

# Configure application-level logging with clean formatting (no INFO: prefix)
logging.basicConfig(level=logging.INFO, format="%(message)s")

for handler in logging.root.handlers:
    handler.addFilter(CleanLogFilter())

# Explicitly suppress chatty third-party libraries (do NOT suppress root!)
for logger_name in ["google", "google.genai", "httpx", "urllib3", "http.client", "absl"]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.ERROR)
    logger.addFilter(CleanLogFilter())

def print_section(step, total, title):
    print(f"\n--------------------------------------------------")
    print(f"[{step}/{total}] {title}")
    print(f"--------------------------------------------------")

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
    print("\n==================================================")
    print("       AI RESUME BUILDER - PIPELINE")
    print("==================================================")
    print("\nWhat would you like to generate?")
    print("1: Resume only")
    print("2: Resume + Cover Letter")
    choice = input("Enter option (1 or 2): ").strip()
    generate_cl = (choice == "2")
    total_steps = 10 if generate_cl else 9
    
    # 1. Parse Job Description (Enhanced — now extracts soft skills, ATS keywords, job type, etc.)
    print_section(1, total_steps, "Parsing Job Description...")
    job_text = read_file(job_file)
    job_reqs = parse_job_description(job_text)
    job_req_text = json.dumps(job_reqs)
    
    job_type = job_reqs.get('job_type', 'unknown')
    job_title = job_reqs.get('job_title', 'Unknown Position')
    logging.info(f"   -> Detected job type: {job_type} | Title: {job_title}")
    logging.info(f"   -> Found {len(job_reqs.get('ats_critical_keywords', []))} ATS critical keywords\n")
    
    # 2. Read Master Resume
    print_section(2, total_steps, "Loading Master Resume...")
    master_resume = read_json(master_resume_path)
    logging.info("   -> Master resume loaded successfully.\n")
    
    # 3. Rank Bullets (semantic similarity)
    print_section(3, total_steps, "Ranking Bullets via Semantic Similarity...")
    ranked_resume = rank_bullets(master_resume, job_req_text)
    logging.info("   -> Semantic bullet ranking completed.\n")
    
    # 4. Rewrite Bullets (aggressive ATS optimization)
    print_section(4, total_steps, "Rewriting Bullets for Maximum ATS Alignment...")
    tailored_resume = rewrite_resume(ranked_resume, job_reqs)
    logging.info("   -> Experience and Project bullets rewritten.\n")
    
    # 5. Tailor Skills Section (dynamic — adapts categories to job type)
    print_section(5, total_steps, "Tailoring Skills Section...")
    tailored_skills = tailor_skills(master_resume.get('technical_skills', {}), job_reqs)
    tailored_resume['technical_skills'] = tailored_skills
    logging.info("   -> Skills categories aligned with job requirements.\n")
    
    # 6. Generate Professional Summary
    print_section(6, total_steps, "Generating Professional Summary...")
    summary_text = generate_professional_summary(tailored_resume, job_reqs)
    logging.info("   -> Professional summary synthesized.\n")
    
    # 7. Tailor Certifications
    print_section(7, total_steps, "Tailoring Certifications...")
    tailored_certs = tailor_certifications(master_resume.get('certifications', []), job_reqs)
    logging.info("   -> Certifications tailored.\n")
    
    # 8. Generate LaTeX (with all new sections)
    print_section(8, total_steps, "Generating Resume LaTeX...")
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
    logging.info(f"   -> LaTeX file saved: {file_name}\n")
    
    # 9. Compile Resume PDF
    print_section(9, total_steps, "Compiling Resume PDF...")
    compile_latex(tex_out_path, output_dir)
    pdf_file = file_name.replace('.tex', '.pdf')
    print(f"\n==================================================")
    print(f" RESUME DONE: {output_dir}/{pdf_file}")
    print(f"==================================================\n")
    
    # 10. Generate Cover Letter if requested
    if generate_cl:
        from cover_letter import generate_cover_letter_data
        from latex_gen import generate_cover_letter_latex
        
        cl_template_path = os.path.join(base_dir, 'data', 'cover_letter_template.tex')
        cl_template_content = read_file(cl_template_path)
        
        print_section(10, total_steps, "Generating & Compiling Cover Letter...")
        cl_data = generate_cover_letter_data(tailored_resume, job_reqs)
        
        logging.info("   -> Generating Cover Letter LaTeX...")
        cl_latex_content = generate_cover_letter_latex(cl_data, cl_template_content)
        
        if short_company_name:
            cl_file_name = f'cover_letter {short_company_name}.tex'
        else:
            cl_file_name = 'cover_letter.tex'
            
        cl_tex_out_path = os.path.join(output_dir, cl_file_name)
        write_file(cl_tex_out_path, cl_latex_content)
        
        logging.info("   -> Compiling Cover Letter PDF...")
        compile_latex(cl_tex_out_path, output_dir)
        cl_pdf_file = cl_file_name.replace('.tex', '.pdf')
        print(f"\n==================================================")
        print(f" COVER LETTER DONE: {output_dir}/{cl_pdf_file}")
        print(f"==================================================\n")

if __name__ == "__main__":
    main()
