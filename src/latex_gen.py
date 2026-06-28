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

def generate_summary_latex(summary_text):
    """Generates the LaTeX for the professional summary section."""
    if not summary_text or not summary_text.strip():
        return ""
    
    escaped_summary = escape_latex(summary_text)
    summary_latex = "\\section{Professional Summary}\n"
    summary_latex += "\\begin{itemize}[leftmargin=0.15in, label={}]\n"
    summary_latex += f"\\small{{\\item{{{escaped_summary}}}}}\n"
    summary_latex += "\\end{itemize}\n"
    return summary_latex

def generate_latex(resume_data, template_content, summary_text="", tailored_certs=None):
    # Summary
    summary_latex = generate_summary_latex(summary_text)
    
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
    if tailored_certs:
        for cert in tailored_certs:
            cert_name = escape_latex(cert.get('name', ''))
            cert_date = escape_latex(cert.get('date', ''))
            cert_latex += "\\resumeProjectHeading\n"
            cert_latex += f"  {{\\textbf{{{cert_name}}}}}{{{cert_date}}}\n"
            cert_latex += "\\resumeItemListStart\n"
            bullets = cert.get('bullets', [])
            if not bullets:
                # Fallback: use description if bullets not available
                desc = cert.get('description', '')
                if desc:
                    cert_latex += f"  \\resumeItem{{{escape_latex(desc)}}}\n"
            else:
                for bullet in bullets[:3]:
                    cert_latex += f"  \\resumeItem{{{escape_latex(bullet)}}}\n"
            cert_latex += "\\resumeItemListEnd\n"
    else:
        # Fallback to default
        cert_latex += "\\resumeProjectHeading\n"
        cert_latex += "  {\\textbf{CompTIA Security+}}{Jan 2025}\n"
        cert_latex += "\\resumeItemListStart\n"
        cert_latex += "  \\resumeItem{Covered threat detection, risk assessment, and vulnerability analysis}\n"
        cert_latex += "  \\resumeItem{Applied encryption, authentication, and network security protocols}\n"
        cert_latex += "  \\resumeItem{Developed understanding of security compliance, incident response, and system protection}\n"
        cert_latex += "\\resumeItemListEnd\n"

    # Inject all placeholders
    latex_out = template_content.replace('{{SUMMARY}}', summary_latex)
    latex_out = latex_out.replace('{{SKILLS}}', skills_latex)
    latex_out = latex_out.replace('{{EXPERIENCE}}', exp_latex)
    latex_out = latex_out.replace('{{PROJECTS}}', proj_latex)
    latex_out = latex_out.replace('{{CERTIFICATIONS}}', cert_latex)
    
    return latex_out

def generate_cover_letter_latex(cl_data, template_content):
    if not cl_data:
        return template_content
        
    latex_out = template_content
    for key, value in cl_data.items():
        placeholder = f"{{{{{key}}}}}"
        latex_out = latex_out.replace(placeholder, escape_latex(str(value)))
        
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
