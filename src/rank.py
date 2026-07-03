"""
Semantic Bullet Ranking Module.
Uses Google Gemini Text Embeddings (gemini-embedding-2) to compute cosine similarity
between candidate resume bullet points and job requirements, filtering for the highest-impact bullets.
"""
import numpy as np
import logging
from google import genai
from google.genai import types

def get_embeddings(texts, client):
    """
    Generates vector embeddings for a list of text strings using the gemini-embedding-2 model.
    
    Args:
        texts (list[str]): List of strings to embed.
        client (google.genai.Client): Initialized Google GenAI SDK client.
        
    Returns:
        list[list[float]]: List of 768-dimensional embedding vectors corresponding to input texts.
                           Returns zero vectors if API embedding fails.
    """
    if not texts:
        return []
    # Replace newlines with spaces for clean sentence representations
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
        # Return zero vectors as fallback if embedding fails
        return [[0.0] * 768 for _ in clean_texts]

def cosine_similarity(a, b):
    """
    Computes the cosine similarity score between two numerical vectors.
    
    Args:
        a (list | np.ndarray): First embedding vector.
        b (list | np.ndarray): Second embedding vector.
        
    Returns:
        float: Cosine similarity score between -1.0 and 1.0 (typically 0.0 to 1.0 for embeddings).
    """
    a = np.array(a)
    b = np.array(b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return np.dot(a, b) / (norm_a * norm_b)

def rank_bullets(master_resume, job_requirements_text):
    """
    Ranks experience and project bullet points by semantic relevance to the job description.
    Keeps the top 5 most relevant bullets per experience item and top 3 projects overall.
    
    Args:
        master_resume (dict): Full candidate master resume dictionary.
        job_requirements_text (str): String representation of parsed job requirements.
        
    Returns:
        dict: A filtered resume dictionary with bullets sorted and pruned by semantic match score.
    """
    client = genai.Client()
    try:
        job_embedding = get_embeddings([job_requirements_text], client)[0]
    except Exception as e:
        logging.error(f"Failed to embed job description: {e}")
        return master_resume
    
    ranked_resume = dict(master_resume)
    
    # Collect all bullets across experience and projects for batched embedding call
    all_bullets = []
    bullet_indices = [] # stores tuple of (section, item_idx, bullet_idx)
    
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
                
    # Batch embed all collected bullets simultaneously for optimal API latency
    if not all_bullets:
        return ranked_resume
        
    logging.info(f"Batch embedding {len(all_bullets)} bullets...")
    bullet_embeddings = get_embeddings(all_bullets, client)
    
    # Data structures to hold scored bullets grouped by parent item
    scored_experience = {i: [] for i in range(len(master_resume.get('experience', [])))}
    scored_projects = {i: [] for i in range(len(master_resume.get('projects', [])))}
    
    # Calculate cosine similarity score for every bullet against job requirements
    for idx, (section, item_idx, bullet_idx) in enumerate(bullet_indices):
        score = cosine_similarity(job_embedding, bullet_embeddings[idx])
        bullet = all_bullets[idx]
        if section == 'experience':
            scored_experience[item_idx].append((score, bullet))
        else:
            scored_projects[item_idx].append((score, bullet))
            
    # Sort and filter Experience items (keep top 5 bullets per role)
    if 'experience' in master_resume:
        ranked_resume['experience'] = []
        for i, exp in enumerate(master_resume.get('experience', [])):
            ranked_exp = dict(exp)
            bullets_with_scores = scored_experience[i]
            bullets_with_scores.sort(key=lambda x: x[0], reverse=True)
            ranked_exp['bullets'] = [b for score, b in bullets_with_scores[:5]]
            ranked_resume['experience'].append(ranked_exp)

    # Sort and filter Project items (keep top 3 bullets per project, and top 3 projects overall)
    if 'projects' in master_resume:
        ranked_resume['projects'] = []
        for i, proj in enumerate(master_resume.get('projects', [])):
            ranked_proj = dict(proj)
            bullets_with_scores = scored_projects[i]
            bullets_with_scores.sort(key=lambda x: x[0], reverse=True)
            ranked_proj['bullets'] = [b for score, b in bullets_with_scores[:3]]
            
            # Calculate average project relevance score based on its top 3 bullets
            proj_score = sum(score for score, b in bullets_with_scores[:3]) / 3 if bullets_with_scores else 0
            ranked_resume['projects'].append((proj_score, ranked_proj))
            
        # Sort projects by average score and keep the top 3 most relevant projects
        ranked_resume['projects'].sort(key=lambda x: x[0], reverse=True)
        ranked_resume['projects'] = [p for score, p in ranked_resume['projects'][:3]]

    return ranked_resume
