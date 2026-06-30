import re
import httpx
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
import logging
from app.config import settings

logger = logging.getLogger(__name__)

def extract_github_username(url: str) -> Optional[str]:
    """
    Extracts the github username from a profile URL.
    """
    if not url or not isinstance(url, str):
        return None
    
    # Matches patterns like github.com/username
    match = re.search(r"github\.com/([a-zA-Z0-9_-]+)", url)
    if match:
        username = match.group(1).strip()
        # Exclude common github paths if misclassified
        if username.lower() in ["settings", "features", "explore", "trending"]:
            return None
        return username
    return None

def make_github_request(url: str) -> Optional[Any]:
    """
    Makes a request to the GitHub API, handling PAT authorization if present.
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Visl-AI-Screening-Platform"
    }
    if settings.GITHUB_PAT:
        headers["Authorization"] = f"token {settings.GITHUB_PAT}"
        
    try:
        with httpx.Client(follow_redirects=True, headers=headers, timeout=15.0) as client:
            response = client.get(url)
            if response.status_code == 403:
                logger.error("GitHub API Rate limit exceeded or forbidden access.")
                return None
            if response.status_code != 200:
                logger.warning(f"GitHub API returned status code {response.status_code} for {url}")
                return None
            return response.json()
    except Exception as e:
        logger.error(f"GitHub API connection error for {url}: {str(e)}")
        return None

def analyze_repo_structure(username: str, repo_name: str) -> Tuple[bool, bool, bool]:
    """
    Queries repo contents root to identify presence of:
    - README (has_readme)
    - Tests directory (has_tests)
    - CI/CD configs (has_ci)
    """
    url = f"https://api.github.com/repos/{username}/{repo_name}/contents"
    contents = make_github_request(url)
    if not contents or not isinstance(contents, list):
        return False, False, False

    has_readme = False
    has_tests = False
    has_ci = False

    for item in contents:
        name_lower = str(item.get("name", "")).lower()
        # Readme detection
        if name_lower.startswith("readme"):
            has_readme = True
        
        # Test directory detection
        if item.get("type") == "dir" and name_lower in ["test", "tests", "spec", "specs", "testing"]:
            has_tests = True
        elif item.get("type") == "file" and (name_lower.startswith("test_") or name_lower.endswith("_test.py") or name_lower.endswith(".test.js") or name_lower.endswith(".spec.ts")):
            has_tests = True

        # CI configuration detection (GitHub Actions, GitLab CI, Travis etc)
        if item.get("type") == "dir" and name_lower == ".github":
            # GitHub actions check
            has_ci = True
        elif item.get("type") == "file" and name_lower in [".gitlab-ci.yml", ".travis.yml", "circle.yml", "jenkinsfile"]:
            has_ci = True

    return has_readme, has_tests, has_ci

def analyze_github_profile(profile_url: str, jd_text: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Fetches the candidate's GitHub repositories, performs profile-level
    and deep repo-level analysis, and calculates a technical score (0-100).
    """
    username = extract_github_username(profile_url)
    if not username:
        return "UNAVAILABLE", {"score": 0.0, "reason": "No valid GitHub username found in URL."}

    # Fetch candidate repositories
    repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=updated"
    repos = make_github_request(repos_url)
    if not repos or not isinstance(repos, list):
        return "UNAVAILABLE", {"score": 0.0, "reason": f"Failed to fetch repositories for GitHub user: {username}"}

    total_repos = len(repos)
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_forks = sum(r.get("forks_count", 0) for r in repos)

    # Compile languages counts
    languages = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    # Analyze commit activity recency (commits in last 6 months)
    recent_commit_count = 0
    now = datetime.now(timezone.utc)
    for r in repos:
        pushed_at_str = r.get("pushed_at")
        if pushed_at_str:
            try:
                # GitHub timestamp format: "2011-01-26T19:01:12Z"
                pushed_at = datetime.strptime(pushed_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                delta_days = (now - pushed_at).days
                if delta_days <= 180:
                    recent_commit_count += 1
            except Exception:
                pass

    # Deep analyze top 3 repos to check quality indicators
    # Sorting repos by updated date
    sorted_repos = sorted(
        repos, 
        key=lambda x: x.get("pushed_at", ""), 
        reverse=True
    )[:3]

    readme_counts = 0
    test_counts = 0
    ci_counts = 0

    top_repos_info = []
    for r in sorted_repos:
        name = r.get("name")
        has_readme, has_tests, has_ci = analyze_repo_structure(username, name)
        
        if has_readme: readme_counts += 1
        if has_tests: test_counts += 1
        if has_ci: ci_counts += 1

        top_repos_info.append({
            "name": name,
            "stars": r.get("stargazers_count", 0),
            "forks": r.get("forks_count", 0),
            "language": r.get("language"),
            "has_readme": has_readme,
            "has_tests": has_tests,
            "has_ci": has_ci
        })

    # Calculate ratios based on the top repos checked (max 3)
    check_count = len(sorted_repos) if len(sorted_repos) > 0 else 1
    has_readme_ratio = readme_counts / check_count
    has_tests_ratio = test_counts / check_count
    has_ci_ratio = ci_counts / check_count

    # --- TECHNICAL SCORE CALCULATION (0-100 Rubric) ---
    score = 0.0
    rubric_breakdown = []

    # 1. Quality Indicators (Max 30 points)
    readme_points = has_readme_ratio * 10
    test_points = has_tests_ratio * 10
    ci_points = has_ci_ratio * 10
    score += (readme_points + test_points + ci_points)
    rubric_breakdown.append(f"Quality Indicators (README/Tests/CI): {round(readme_points + test_points + ci_points, 1)}/30")

    # 2. Activity Recency & Commit Frequency (Max 20 points)
    recency_points = 0
    if len(sorted_repos) > 0:
        # Check pushes in last 30 days
        most_recent_str = sorted_repos[0].get("pushed_at")
        if most_recent_str:
            try:
                most_recent = datetime.strptime(most_recent_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                days_since = (now - most_recent).days
                if days_since <= 30:
                    recency_points += 10
                elif days_since <= 90:
                    recency_points += 5
            except Exception:
                pass
    # Commit frequency points (+2 per active repository in last 6 months, up to 10 points)
    frequency_points = min(recent_commit_count * 2, 10)
    score += (recency_points + frequency_points)
    rubric_breakdown.append(f"Recent Activity (Commit frequency/recency): {recency_points + frequency_points}/20")

    # 3. Popularity & Reach (Max 20 points)
    # +2 points per star (max 10 points), +2 points per fork (max 10 points)
    star_points = min(total_stars * 2, 10)
    fork_points = min(total_forks * 2, 10)
    score += (star_points + fork_points)
    rubric_breakdown.append(f"Popularity & Impact (Stars/Forks): {star_points + fork_points}/20")

    # 4. Job Description Relevance & Match (Max 30 points)
    # We examine whether candidate languages match the JD context
    jd_match_points = 15.0 # Default base points for active repos
    if jd_text and languages:
        jd_text_lower = jd_text.lower()
        matched_languages = []
        for lang in languages:
            if lang.lower() in jd_text_lower:
                matched_languages.append(lang)
        # Scale score based on matches
        if matched_languages:
            jd_match_points = min(15.0 + (len(matched_languages) * 5), 30.0)
    score += jd_match_points
    rubric_breakdown.append(f"Tech Stack Match (Language alignment): {jd_match_points}/30")

    score_details = {
        "github_username": username,
        "total_repos": total_repos,
        "languages": languages,
        "total_stars": total_stars,
        "total_forks": total_forks,
        "recent_commit_count": recent_commit_count,
        "has_readme_ratio": has_readme_ratio,
        "has_tests_ratio": has_tests_ratio,
        "has_ci_ratio": has_ci_ratio,
        "top_repos": top_repos_info,
        "score": score,
        "reason": f"GitHub analysis completed successfully. Rubric breakdown: {', '.join(rubric_breakdown)}."
    }

    return "EXTRACTED", score_details
