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
    
    # Check user preference
    print("\nWhat would you like to generate?")
    print("1: Resume only")
    print("2: Resume + Cover Letter")
    choice = input("Enter option (1 or 2): ").strip()
    generate_cl = (choice == "2")
    
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
    logging.info("Generating Resume LaTeX...")
    template_content = read_file(template_path)
    latex_content = generate_latex(tailored_resume, template_content)
    
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
    
    # 6. Compile Resume PDF
    logging.info("Compiling Resume PDF...")
    compile_latex(tex_out_path, output_dir)
    pdf_file = file_name.replace('.tex', '.pdf')
    logging.info(f"Resume Done! Check {output_dir}/{pdf_file}")

    # 7. Generate Cover Letter if requested
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
