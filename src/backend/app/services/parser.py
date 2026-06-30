import io
import pandas as pd
from typing import Tuple, List, Dict, Any, Union

def parse_upload_file(file_content: bytes, file_name: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Parses CSV/XLSX file contents.
    Auto-detects whether the file represents the full Candidate Response sheet or a Test Result sheet.
    Returns:
        Tuple[str, List[Dict[str, Any]]]: (detected_type, normalized_records)
        where detected_type is either 'candidate_response' or 'test_result'.
    """
    # 1. Load file into a pandas DataFrame
    file_lower = file_name.lower()
    try:
        if file_lower.endswith('.xlsx') or file_lower.endswith('.xls'):
            # Load the first sheet
            df = pd.read_excel(io.BytesIO(file_content))
        else:
            # Fallback to CSV
            df = pd.read_csv(io.BytesIO(file_content))
    except Exception as e:
        raise ValueError(f"Failed to read file format: {str(e)}")

    # 2. Normalize and clean columns
    # Strip whitespace, convert to lowercase, replace spaces/dots with underscores
    original_cols = list(df.columns)
    df.columns = [str(c).strip().lower().replace(" ", "_").replace(".", "_") for c in df.columns]

    # Map column aliases back to standard schema fields if needed
    col_mapping = {
        's_no': 's_no',
        'sno': 's_no',
        'name': 'name',
        'candidate_name': 'name',
        'email': 'email',
        'email_address': 'email',
        'college': 'college',
        'university': 'college',
        'branch': 'branch',
        'major': 'branch',
        'cgpa': 'cgpa',
        'gpa': 'cgpa',
        'best_ai_project': 'best_ai_project',
        'ai_project': 'best_ai_project',
        'research_work': 'research_work',
        'research': 'research_work',
        'github': 'github',
        'github_profile': 'github',
        'github_url': 'github',
        'resume': 'resume',
        'resume_link': 'resume',
        'test_la': 'test_la',
        'logical_aptitude': 'test_la',
        'test_code': 'test_code',
        'coding_score': 'test_code'
    }

    # Rename columns to standard ones based on mapping
    rename_dict = {}
    for col in df.columns:
        if col in col_mapping:
            rename_dict[col] = col_mapping[col]
    df = df.rename(columns=rename_dict)

    # 3. Detect sheet type by column signature
    required_response_cols = {'name', 'email', 'best_ai_project', 'resume'}
    required_test_cols = {'email', 'test_la', 'test_code'}

    current_cols = set(df.columns)

    if required_response_cols.issubset(current_cols):
        detected_type = 'candidate_response'
    elif required_test_cols.issubset(current_cols):
        detected_type = 'test_result'
    else:
        # Fallback heuristic: check if it looks like a candidate sheet
        if 'email' in current_cols and ('github' in current_cols or 'resume' in current_cols):
            detected_type = 'candidate_response'
        elif 'email' in current_cols and ('test_la' in current_cols or 'test_code' in current_cols):
            detected_type = 'test_result'
        else:
            raise ValueError(
                f"Could not auto-detect sheet type. Columns present: {original_cols}. "
                f"Candidate sheet requires at least: name, email, best_ai_project, resume. "
                f"Test results require: email, test_la, test_code."
            )

    # Replace all NaN/None values with None for database compatibility
    df = df.where(pd.notnull(df), None)

    records = []
    # 4. Ingest & Normalize Records
    for index, row in df.iterrows():
        record = row.to_dict()
        
        # Strip all string values
        for key in record:
            if isinstance(record[key], str):
                record[key] = record[key].strip()

        # Email must be lowercase and present
        if not record.get('email'):
            continue  # Skip rows without email
        record['email'] = str(record['email']).lower()

        # Normalize CGPA
        if 'cgpa' in record and record['cgpa'] is not None:
            try:
                record['cgpa'] = float(record['cgpa'])
            except (ValueError, TypeError):
                record['cgpa'] = None

        # Normalize s_no
        if 's_no' in record and record['s_no'] is not None:
            try:
                record['s_no'] = int(record['s_no'])
            except (ValueError, TypeError):
                record['s_no'] = index + 1
        else:
            record['s_no'] = index + 1

        # Normalize test scores
        for score_key in ['test_la', 'test_code']:
            if score_key in record and record[score_key] is not None:
                try:
                    record[score_key] = float(record[score_key])
                except (ValueError, TypeError):
                    record[score_key] = 0.0

        records.append(record)

    return detected_type, records
