import sys
import os
import json
import logging
from utils import load_env, read_file, read_json, write_file
from parse_job import parse_job_description
from rank import rank_bullets
from rewrite import rewrite_resume
from latex_gen import generate_latex, compile_latex

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
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
    
    # 1. Parse Job Description
    logging.info("Parsing job description...")
    job_text = read_file(job_file)
    job_reqs = parse_job_description(job_text)
    job_req_text = json.dumps(job_reqs)
    
    # 2. Read Master Resume
    logging.info("Loading master resume...")
    master_resume = read_json(master_resume_path)
    
    # 3. Rank Bullets
    logging.info("Ranking bullets via semantic similarity...")
    ranked_resume = rank_bullets(master_resume, job_req_text)
    
    # 4. Rewrite Bullets
    logging.info("Rewriting bullets for alignment...")
    tailored_resume = rewrite_resume(ranked_resume, job_reqs)
    
    # 5. Generate LaTeX
    logging.info("Generating LaTeX...")
    template_content = read_file(template_path)
    latex_content = generate_latex(tailored_resume, template_content)
    
    company_name = job_reqs.get('company_name', '').strip()
    if company_name:
        clean_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '_', '-')).replace(' ', '_')
        file_name = f'resume_{clean_company_name}.tex'
    else:
        file_name = 'resume.tex'
        
    tex_out_path = os.path.join(output_dir, file_name)
    write_file(tex_out_path, latex_content)
    
    # 6. Compile PDF
    logging.info("Compiling PDF...")
    compile_latex(tex_out_path, output_dir)
    pdf_file = file_name.replace('.tex', '.pdf')
    logging.info(f"Done! Check {output_dir}/{pdf_file}")

if __name__ == "__main__":
    main()
