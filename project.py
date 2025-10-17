# project.py

import os
import json
from google import genai
from google.genai import types

GEMINI_API_KEY = "AIzaSyBMOheVL6Hb33V8G3XhDr4N508CtA7wy00"

# --- Configuration ---
MODEL_NAME = 'gemini-2.5-flash'
TEMPERATURE = 0.3
INPUT_DIR = 'sample_inputs'
OUTPUT_DIR = 'outputs'
JD_FILE = os.path.join(INPUT_DIR, 'jd.txt')
CV_FILES = [
    os.path.join(INPUT_DIR, 'cv1.txt'),
    os.path.join(INPUT_DIR, 'cv2.txt'),
    os.path.join(INPUT_DIR, 'cv3.txt')
]
PROMPT_FILE = 'prompt.md'
# --- JSON Structure defined in the project description ---
EXPECTED_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "match_score": {"type": "integer", "description": "0-100"},
        "summary": {"type": "string", "description": "Īss apraksts, cik labi CV atbilst JD."},
        "strengths": {"type": "array", "items": {"type": "string"}, "description": "Galvenās prasmes/pieredze no CV, kas atbilst JD"},
        "missing_requirements": {"type": "array", "items": {"type": "string"}, "description": "Svarīgas JD prasības, kas CV nav redzamas"},
        "verdict": {"type": "string", "description": "strong match | possible match | not a match"}
    },
    "required": ["match_score", "summary", "strengths", "missing_requirements", "verdict"]
}

def load_file_content(filepath):
    """Loads and returns the content of a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found: {filepath}")
        return None

def generate_report(cv_json, cv_filename):
    """Generates a brief Markdown report from the JSON output."""
    data = cv_json
    report = f"# CV Match Report: {cv_filename}\n\n"
    report += f"**Match Score:** {data.get('match_score', 'N/A')}/100\n"
    report += f"**Hiring Verdict:** **{data.get('verdict', 'N/A')}**\n\n"
    report += "---\n\n"
    report += f"## Summary\n"
    report += f"{data.get('summary', 'No summary provided.')}\n\n"
    report += f"## Strengths (Matching JD Requirements)\n"
    if data.get('strengths'):
        report += "\n".join([f"* {s}" for s in data['strengths']])
    else:
        report += "* None identified.\n"
    report += "\n\n## Missing Requirements (from JD)\n"
    if data.get('missing_requirements'):
        report += "\n".join([f"* {m}" for m in data['missing_requirements']])
    else:
        report += "* None identified.\n"

    return report

def process_cv(client, jd_text, cv_path, prompt_template):
    """Processes a single CV using the Gemini API."""
    cv_filename = os.path.basename(cv_path)
    cv_id = cv_filename.split('.')[0] # e.g., 'cv1'

    print(f"\n--- Processing {cv_filename} ---")
    cv_text = load_file_content(cv_path)
    if not cv_text:
        return

    # 2. Sagatavojiet promptu: apvieno JD un CV tekstu
    full_prompt = prompt_template.replace('{{JOB_DESCRIPTION}}', jd_text).replace('{{CANDIDATE_CV}}', cv_text)

    # 3. Izsauciet Gemini Flash 2.5
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=TEMPERATURE,
                response_mime_type="application/json",
                response_schema=EXPECTED_JSON_SCHEMA,
            ),
        )

        # Pārsēdz JSON atbildi no teksta uz Python dict
        cv_json = json.loads(response.text)
        print(f"Model response received for {cv_id}. Match Score: {cv_json.get('match_score', 'N/A')}, Verdict: {cv_json.get('verdict', 'N/A')}")

        # 4. Saglabājiet modeli atbildi kā outputs/cvN.json
        json_output_path = os.path.join(OUTPUT_DIR, f'{cv_id}.json')
        with open(json_output_path, 'w', encoding='utf-8') as f:
            json.dump(cv_json, f, indent=4, ensure_ascii=False)
        print(f"Saved JSON to: {json_output_path}")

        # 5. Ģenerējiet īsu pārskatu
        report_content = generate_report(cv_json, cv_filename)
        report_output_path = os.path.join(OUTPUT_DIR, f'{cv_id}_report.md')
        with open(report_output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"Saved Report to: {report_output_path}")

    except Exception as e:
        print(f"An error occurred during API call or processing for {cv_id}: {e}")


def main():
    """Main function to orchestrate the CV grading project."""
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        print("ERROR: Please insert your GEMINI_API_KEY in project.py.")
        return

    # Pārliecināties, ka nepieciešamās mapes eksistē
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Inicēt Gemini klientu
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")
        return

    # 1. Nolasiet darba aprakstu un promptu
    jd_text = load_file_content(JD_FILE)
    prompt_template = load_file_content(PROMPT_FILE)

    if not jd_text or not prompt_template:
        print("Required input or prompt files are missing. Please create them.")
        return

    # 6. Atkārtojiet 2.-5. soli visiem trim CV.
    for cv_path in CV_FILES:
        process_cv(client, jd_text, cv_path, prompt_template)

    print("\n--- All CVs processed. ---")

if __name__ == "__main__":
    # Pārliecināties, ka ir instalēta google-genai bibliotēka:
    # pip install google-genai
    main()