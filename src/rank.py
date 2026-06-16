import numpy as np
import logging
from google import genai
from google.genai import types

def get_embeddings(texts, client):
    if not texts:
        return []
    clean_texts = [str(t).replace("\n", " ") for t in texts]
    try:
        response = client.models.embed_content(
            model="gemini-embedding-2",
            contents=clean_texts,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
        )
        return [emb.values for emb in response.embeddings]
    except Exception as e:
        logging.error(f"Failed to batch embed: {e}")
        # Return zero vectors if failure
        return [[0.0] * 768 for _ in clean_texts]

def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return np.dot(a, b) / (norm_a * norm_b)

def rank_bullets(master_resume, job_requirements_text):
    client = genai.Client()
    try:
        job_embedding = get_embeddings([job_requirements_text], client)[0]
    except Exception as e:
        logging.error(f"Failed to embed job description: {e}")
        return master_resume
    
    ranked_resume = dict(master_resume)
    
    # Collect all bullets
    all_bullets = []
    bullet_indices = [] # stores (section, item_idx, bullet_idx)
    
    if 'experience' in master_resume:
        for i, exp in enumerate(master_resume.get('experience', [])):
            for j, bullet in enumerate(exp.get('bullets', [])):
                all_bullets.append(bullet)
                bullet_indices.append(('experience', i, j))
                
    if 'projects' in master_resume:
        for i, proj in enumerate(master_resume.get('projects', [])):
            for j, bullet in enumerate(proj.get('bullets', [])):
                all_bullets.append(bullet)
                bullet_indices.append(('projects', i, j))
                
    # Batch embed all bullets
    if not all_bullets:
        return ranked_resume
        
    logging.info(f"Batch embedding {len(all_bullets)} bullets...")
    bullet_embeddings = get_embeddings(all_bullets, client)
    
    # Structure for scoring
    scored_experience = {i: [] for i in range(len(master_resume.get('experience', [])))}
    scored_projects = {i: [] for i in range(len(master_resume.get('projects', [])))}
    
    for idx, (section, item_idx, bullet_idx) in enumerate(bullet_indices):
        score = cosine_similarity(job_embedding, bullet_embeddings[idx])
        bullet = all_bullets[idx]
        if section == 'experience':
            scored_experience[item_idx].append((score, bullet))
        else:
            scored_projects[item_idx].append((score, bullet))
            
    # Rank Experience
    if 'experience' in master_resume:
        ranked_resume['experience'] = []
        for i, exp in enumerate(master_resume.get('experience', [])):
            ranked_exp = dict(exp)
            bullets_with_scores = scored_experience[i]
            bullets_with_scores.sort(key=lambda x: x[0], reverse=True)
            ranked_exp['bullets'] = [b for score, b in bullets_with_scores[:3]]
            ranked_resume['experience'].append(ranked_exp)

    # Rank Projects
    if 'projects' in master_resume:
        ranked_resume['projects'] = []
        for i, proj in enumerate(master_resume.get('projects', [])):
            ranked_proj = dict(proj)
            bullets_with_scores = scored_projects[i]
            bullets_with_scores.sort(key=lambda x: x[0], reverse=True)
            ranked_proj['bullets'] = [b for score, b in bullets_with_scores[:2]]
            
            proj_score = sum(score for score, b in bullets_with_scores[:2]) / 2 if bullets_with_scores else 0
            ranked_resume['projects'].append((proj_score, ranked_proj))
            
        # Keep only top 2 projects
        ranked_resume['projects'].sort(key=lambda x: x[0], reverse=True)
        ranked_resume['projects'] = [p for score, p in ranked_resume['projects'][:2]]

    return ranked_resume
