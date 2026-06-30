import os
import yaml
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "jd_relevance": 0.30,
    "project_quality": 0.20,
    "github_technical": 0.20,
    "academic": 0.10,
    "test_performance": 0.20
}

def load_scoring_weights() -> Dict[str, float]:
    """
    Loads weights from scoring_config.yaml or falls back to defaults.
    """
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "scoring_config.yaml"
    )
    if not os.path.exists(config_path):
        return DEFAULT_WEIGHTS
        
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            weights = config.get("weights", DEFAULT_WEIGHTS)
            # Validate total sum is close to 1.0
            total = sum(weights.values())
            if not (0.99 <= total <= 1.01):
                logger.warning(f"Scoring weights sum to {total}, which is not 1.0. Readjusting to defaults.")
                return DEFAULT_WEIGHTS
            return weights
    except Exception as e:
        logger.error(f"Failed to load scoring_config.yaml: {str(e)}")
        return DEFAULT_WEIGHTS

def normalize_academic_score(cgpa: Any) -> float:
    """
    Normalizes CGPA to 0-100 scale.
    Assumes standard scale is 10.0 (multiplier of 10).
    If <= 4.0, assumes US 4.0 scale (multiplier of 25).
    If > 10.0, assumes percentage (uses directly).
    """
    if cgpa is None:
        return 0.0
    try:
        cgpa_val = float(cgpa)
        if cgpa_val <= 4.0:
            return cgpa_val * 25.0
        elif cgpa_val <= 10.0:
            return cgpa_val * 10.0
        else:
            return min(cgpa_val, 100.0)
    except (ValueError, TypeError):
        return 0.0

def calculate_composite_score(
    jd_relevance: Optional[float],
    project_quality: Optional[float],
    github_technical: Optional[float],
    cgpa: Optional[float],
    test_la: Optional[float],
    test_code: Optional[float]
) -> float:
    """
    Calculates candidate composite score out of 100 based on weights configuration.
    """
    weights = load_scoring_weights()
    
    # 1. Normalize sub-scores (0-100 scale)
    jd_score = float(jd_relevance) if jd_relevance is not None else 0.0
    proj_score = float(project_quality) if project_quality is not None else 0.0
    git_score = float(github_technical) if github_technical is not None else 0.0
    
    acad_score = normalize_academic_score(cgpa)
    
    # Test Performance Formula (40% Logical Aptitude + 60% Coding Score)
    la_score = float(test_la) if test_la is not None else 0.0
    code_score = float(test_code) if test_code is not None else 0.0
    
    test_perf_score = (0.40 * la_score) + (0.60 * code_score)

    # 2. Compute Weighted Sum
    composite = (
        weights["jd_relevance"] * jd_score +
        weights["project_quality"] * proj_score +
        weights["github_technical"] * git_score +
        weights["academic"] * acad_score +
        weights["test_performance"] * test_perf_score
    )

    return round(composite, 2)
