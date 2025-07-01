from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import fitz  # PyMuPDF
import csv
import os
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
RESULTS_CSV = "results.csv"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/evaluate', methods=['POST'])
def evaluate():
    file = request.files['pdf']
    category = request.form.get('category')
    zone = request.form.get('zone')

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    with fitz.open(file_path) as doc:
        full_text = "\n".join([page.get_text() for page in doc])

    # Extract candidate metadata
    name = re.search(r"Candidate Name\s+(.*)", full_text)
    community = re.search(r"Community\s+(.*)", full_text)
    center = re.search(r"Test Center Name\s+(.*)", full_text)
    test_date = re.search(r"Test Date\s+(.*)", full_text)
    test_time = re.search(r"Test Time\s+(.*)", full_text)

    name = name.group(1).strip() if name else "N/A"
    community = community.group(1).strip() if community else "N/A"
    center = center.group(1).strip() if center else "N/A"
    test_date = test_date.group(1).strip() if test_date else "N/A"
    test_time = test_time.group(1).strip() if test_time else "N/A"

    question_blocks = full_text.split("Q.")
    correct = wrong = unattempted = 0
    q_index = 0

    with fitz.open(file_path) as doc:
        for block in question_blocks:
            if not block.strip():
                continue

            status_match = re.search(r"Status\s*:\s*(.*?)\n", block)
            chosen_match = re.search(r"Chosen Option\s*:\s*(\d)", block)

            status = status_match.group(1).strip() if status_match else "Not Answered"
            chosen_option = chosen_match.group(1).strip() if chosen_match else None

            if status.lower() != "answered" or not chosen_option:
                unattempted += 1
                q_index += 1
                continue

            correct_option = None
            question_found = False
            question_label = f"Q.{q_index + 1}"

            for page in doc:
                blocks = page.get_text("dict")["blocks"]
                for b in blocks:
                    if "lines" not in b:
                        continue
                    for l in b["lines"]:
                        for s in l["spans"]:
                            if question_label in s["text"]:
                                question_found = True
                            if not question_found:
                                continue
                            color = s.get("color", 0)
                            text = s["text"]
                            # Match "1. Windows 95", "2. Linux", etc.
                            if color in [32768, 65280]:  # green shades
                                match = re.match(r"(\d)\.\s", text)
                                if match:
                                    correct_option = match.group(1)
                                    question_found = False
                                    break
                        if correct_option:
                            break
                    if correct_option:
                        break
                if correct_option:
                    break

            q_index += 1

            if not correct_option:
                wrong += 1
                continue

            if chosen_option == correct_option:
                correct += 1
            else:
                wrong += 1

    total_answered = correct + wrong
    final_mark = round(correct * 1 - wrong * 0.3, 2)

    with open(RESULTS_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now(), name, community, center, test_date, test_time,
            category, zone, total_answered, correct, wrong, final_mark
        ])

    return jsonify({
        "name": name,
        "community": community,
        "center": center,
        "test_date": test_date,
        "test_time": test_time,
        "answered": total_answered,
        "correct": correct,
        "wrong": wrong,
        "score": final_mark
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
