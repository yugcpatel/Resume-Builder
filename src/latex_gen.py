import os
import subprocess
import logging

def escape_latex(text):
    if not isinstance(text, str):
        return str(text)
    
    chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}'
    }
    escaped = ''.join(chars.get(c, c) for c in text)
    return escaped

def generate_latex(resume_data, template_content):
    # Education
    edu_latex = ""
    for edu in resume_data.get('education', []):
        inst = escape_latex(edu.get('institution', ''))
        loc = escape_latex(edu.get('location', ''))
        deg = escape_latex(edu.get('degree', ''))
        major = escape_latex(edu.get('major', ''))
        start = escape_latex(edu.get('start_date', ''))
        end = escape_latex(edu.get('end_date', ''))
        
        edu_latex += f"\\resumeSubheading\n"
        edu_latex += f"  {{{inst}}}{{{loc}}}\n"
        edu_latex += f"  {{{deg} in {major}}}{{{start} -- {end}}}\n"

    # Skills
    skills_data = resume_data.get('technical_skills', {})
    skills_latex = ""
    for category, skills_list in skills_data.items():
        if isinstance(skills_list, list):
            cat_name = escape_latex(category.replace('_', ' ').title())
            skills_str = escape_latex(", ".join(skills_list))
            skills_latex += f"\\textbf{{{cat_name}}}{{: {skills_str}}} \\\\\n"

    # Experience
    exp_latex = ""
    for exp in resume_data.get('experience', []):
        title = escape_latex(exp.get('title', ''))
        company = escape_latex(exp.get('company', ''))
        loc = escape_latex(exp.get('location', ''))
        start = escape_latex(exp.get('start_date', ''))
        end = escape_latex(exp.get('end_date', ''))
        
        exp_latex += f"\\resumeSubheading\n"
        exp_latex += f"  {{{title}}}{{{start} -- {end}}}\n"
        exp_latex += f"  {{{company}}}{{{loc}}}\n"
        exp_latex += "\\resumeItemListStart\n"
        for bullet in exp.get('bullets', []):
            exp_latex += f"  \\resumeItem{{{escape_latex(bullet)}}}\n"
        exp_latex += "\\resumeItemListEnd\n"
        
    # Projects
    proj_latex = ""
    for proj in resume_data.get('projects', []):
        name = escape_latex(proj.get('name', ''))
        type_ = escape_latex(proj.get('type', ''))
        start = escape_latex(proj.get('start_date', ''))
        end = escape_latex(proj.get('end_date', ''))
        
        proj_latex += f"\\resumeProjectHeading\n"
        proj_latex += f"  {{\\textbf{{{name}}} $|$ \\emph{{{type_}}}}}{{{start} -- {end}}}\n"
        proj_latex += "\\resumeItemListStart\n"
        for bullet in proj.get('bullets', []):
            proj_latex += f"  \\resumeItem{{{escape_latex(bullet)}}}\n"
        proj_latex += "\\resumeItemListEnd\n"

    # Certifications
    cert_latex = ""
    for cert in resume_data.get('certifications', []):
        name = escape_latex(cert.get('name', ''))
        date = escape_latex(cert.get('date', ''))
        
        # Join details to save space
        details = [escape_latex(d) for d in cert.get('details', [])]
        details_str = ", ".join(details)
        # Prevent it from being too long, take the first 3 or truncate
        if len(details_str) > 88:
            details_str = details_str[:85] + "..."
            
        cert_latex += f"\\resumeProjectHeading\n"
        if details_str:
            cert_latex += f"  {{\\textbf{{{name}}} $|$ \\emph{{{details_str}}}}}{{{date}}}\n"
        else:
            cert_latex += f"  {{\\textbf{{{name}}}}}{{{date}}}\n"

    # Inject
    latex_out = template_content.replace('{{EDUCATION}}', edu_latex)
    latex_out = latex_out.replace('{{SKILLS}}', skills_latex)
    latex_out = latex_out.replace('{{EXPERIENCE}}', exp_latex)
    latex_out = latex_out.replace('{{PROJECTS}}', proj_latex)
    latex_out = latex_out.replace('{{CERTIFICATIONS}}', cert_latex)
    
    return latex_out

def compile_latex(tex_path, output_dir):
    import shutil
    try:
        pdflatex_cmd = 'pdflatex'
        if not shutil.which(pdflatex_cmd):
            user_profile = os.environ.get('USERPROFILE', '')
            miktex_path = os.path.join(user_profile, 'AppData', 'Local', 'Programs', 'MiKTeX', 'miktex', 'bin', 'x64', 'pdflatex.exe')
            miktex_path_2 = r"C:\Program Files\MiKTeX\miktex\bin\x64\pdflatex.exe"
            if os.path.exists(miktex_path):
                pdflatex_cmd = miktex_path
            elif os.path.exists(miktex_path_2):
                pdflatex_cmd = miktex_path_2

        result = subprocess.run(
            [pdflatex_cmd, '-output-directory', output_dir, tex_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            logging.error(f"pdflatex failed:\n{result.stderr}\n{result.stdout}")
        else:
            logging.info("PDF compiled successfully.")
    except FileNotFoundError:
        logging.error("pdflatex not found. Please ensure LaTeX is installed and in your PATH.")
    except Exception as e:
        logging.error(f"Error compiling LaTeX: {e}")
