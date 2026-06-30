import httpx
import json
import logging
from typing import Optional, Dict, Any, Tuple
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert technical recruiter. You evaluate candidates against a Job Description (JD).
You must output a single JSON object. Do not include markdown code block styling or any leading/trailing explanations. 
Your output must conform exactly to this schema:
{
  "jd_relevance_score": 85.0,
  "jd_relevance_rationale": "2-3 sentences explaining the candidate's alignment with core requirements, based on resume skills.",
  "jd_matched_skills": ["Python", "Machine Learning", "FastAPI"],
  "jd_missing_skills": ["Docker", "Kubernetes"],
  "project_quality_score": 90.0,
  "project_quality_rationale": "2-3 sentences evaluating the best AI project and research work for technical depth, novelty, and rigor."
}
All scores must be floats between 0.0 and 100.0. Under 'project_quality_rationale', focus specifically on verifiability and depth.
"""

def generate_heuristic_fallback(resume_text: str, jd_text: str, best_project: str, research: str) -> Dict[str, Any]:
    """
    Generates a deterministic keyword-based evaluation fallback in case the LLM API is unavailable.
    """
    resume_lower = (resume_text or "").lower()
    jd_lower = (jd_text or "").lower()
    project_lower = (best_project or "").lower()
    research_lower = (research or "").lower()

    # Define some standard keywords to look for matches
    common_skills = [
        "python", "javascript", "typescript", "react", "vue", "node", "express", 
        "fastapi", "django", "flask", "docker", "kubernetes", "aws", "gcp", "azure", 
        "sql", "postgresql", "mongodb", "redis", "celery", "machine learning", "ml",
        "deep learning", "nlp", "vision", "transformers", "pytorch", "tensorflow"
    ]
    
    matched = []
    missing = []
    
    # Simple check for matches
    for skill in common_skills:
        if skill in jd_lower:
            if skill in resume_lower or skill in project_lower or skill in research_lower:
                matched.append(skill.capitalize())
            else:
                missing.append(skill.capitalize())

    # Score relevance based on ratio of matched skills
    total_jd_skills = len(matched) + len(missing)
    if total_jd_skills > 0:
        jd_score = (len(matched) / total_jd_skills) * 100
        # Give a small boost for base matches
        jd_score = min(50.0 + (jd_score * 0.5), 100.0)
    else:
        jd_score = 65.0 # default baseline

    # Score project based on length/keywords
    project_length = len(best_project or "") + len(research or "")
    if project_length > 250:
        proj_score = 85.0
        proj_rationale = "Candidate provided high depth detail on projects, demonstrating verified practical implementations."
    elif project_length > 50:
        proj_score = 70.0
        proj_rationale = "Candidate provided basic project descriptions with average technical explanation."
    else:
        proj_score = 40.0
        proj_rationale = "Candidate provided minimal or no project/research text context."

    matched_str = matched if matched else ["Software Engineering"]
    missing_str = missing if missing else ["AI System Design"]

    return {
        "jd_relevance_score": round(jd_score, 1),
        "jd_relevance_rationale": f"Fallback evaluation completed (API inactive). Matched {len(matched)} skills, missing {len(missing)} requirements.",
        "jd_matched_skills": matched_str,
        "jd_missing_skills": missing_str,
        "project_quality_score": round(proj_score, 1),
        "project_quality_rationale": proj_rationale
    }

def evaluate_candidate_with_llm(
    resume_text: str, 
    best_project: str, 
    research: str, 
    jd_text: str
) -> Tuple[Dict[str, Any], str, str]:
    """
    Assembles prompts, calls Groq API using JSON mode, parses the response,
    and returns (parsed_json_dict, full_prompt_sent, raw_response_received).
    """
    user_prompt = f"""Evaluate this candidate for the Job Description.

--- JOB DESCRIPTION ---
{jd_text}

--- CANDIDATE RESUME TEXT ---
{resume_text or "No resume uploaded."}

--- BEST AI PROJECT SUMMARY ---
{best_project or "None provided."}

--- RESEARCH WORK SUMMARY ---
{research or "None provided."}
"""

    full_prompt = f"SYSTEM:\n{SYSTEM_PROMPT}\n\nUSER:\n{user_prompt}"

    # Return fallback if API key is not set
    if not settings.GROQ_API_KEY:
        logger.warning("GROQ_API_KEY is not configured. Falling back to heuristic scorer.")
        fallback = generate_heuristic_fallback(resume_text, jd_text, best_project, research)
        return fallback, full_prompt, json.dumps(fallback)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Groq JSON mode options
    payload = {
        "model": "llama3-70b-8192",  # Default fast large reasoning model
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2
    }

    raw_response = ""
    for attempt in range(3):
        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    raw_response = data["choices"][0]["message"]["content"]
                    # Try parsing the raw JSON
                    parsed = json.loads(raw_response)
                    
                    # Basic validation of keys
                    required_keys = {
                        "jd_relevance_score", "jd_relevance_rationale", 
                        "jd_matched_skills", "jd_missing_skills", 
                        "project_quality_score", "project_quality_rationale"
                    }
                    if required_keys.issubset(parsed.keys()):
                        return parsed, full_prompt, raw_response
                else:
                    logger.warning(f"Groq API returned status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Error calling Groq API on attempt {attempt+1}: {str(e)}")

    # Final fallback if all attempts fail
    logger.warning("Groq API calls failed or yielded malformed JSON. Initiating fallback scorer.")
    fallback = generate_heuristic_fallback(resume_text, jd_text, best_project, research)
    return fallback, full_prompt, raw_response if raw_response else json.dumps(fallback)
