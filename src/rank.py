import numpy as np
import logging
from google import genai
from google.genai import types

def get_embedding(text, client):
    text = str(text).replace("\n", " ")
    response = client.models.embed_content(
        model="gemini-embedding-2",
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
    )
    return response.embeddings[0].values

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def rank_bullets(master_resume, job_requirements_text):
    client = genai.Client()
    try:
        job_embedding = get_embedding(job_requirements_text, client)
    except Exception as e:
        logging.error(f"Failed to embed job description: {e}")
        return master_resume
    
    ranked_resume = dict(master_resume)
    
    # Rank Experience
    if 'experience' in master_resume:
        ranked_resume['experience'] = []
        for exp in master_resume.get('experience', []):
            ranked_exp = dict(exp)
            bullets_with_scores = []
            for bullet in exp.get('bullets', []):
                try:
                    bullet_embedding = get_embedding(bullet, client)
                    score = cosine_similarity(job_embedding, bullet_embedding)
                    bullets_with_scores.append((score, bullet))
                except Exception as e:
                    logging.error(f"Embedding failed for bullet: {e}")
                    bullets_with_scores.append((0, bullet))
            
            bullets_with_scores.sort(key=lambda x: x[0], reverse=True)
            top_bullets = [b for score, b in bullets_with_scores[:3]]
            ranked_exp['bullets'] = top_bullets
            ranked_resume['experience'].append(ranked_exp)

    # Rank Projects
    if 'projects' in master_resume:
        ranked_resume['projects'] = []
        for proj in master_resume.get('projects', []):
            ranked_proj = dict(proj)
            bullets_with_scores = []
            for bullet in proj.get('bullets', []):
                try:
                    bullet_embedding = get_embedding(bullet, client)
                    score = cosine_similarity(job_embedding, bullet_embedding)
                    bullets_with_scores.append((score, bullet))
                except Exception as e:
                    logging.error(f"Embedding failed for bullet: {e}")
                    bullets_with_scores.append((0, bullet))
            
            bullets_with_scores.sort(key=lambda x: x[0], reverse=True)
            top_bullets = [b for score, b in bullets_with_scores[:2]]
            ranked_proj['bullets'] = top_bullets
            ranked_resume['projects'].append(ranked_proj)

    return ranked_resume
