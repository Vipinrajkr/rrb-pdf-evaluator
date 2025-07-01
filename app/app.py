from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import fitz  # PyMuPDF
import csv
import os
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS so frontend (like WordPress) can connect

UPLOAD_FOLDER = "uploads"
RESULTS_CSV = "results.csv"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')  # Optional browser form

@app.route('/evaluate', methods=['POST'])
def evaluate():
    file = request.files['pdf']
    category = request.form.get('category')
    zone = request.form.get('zone')

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    with fitz.open(file_path) as doc:
        text = ""
        for page in doc:
            text += page.get_text()

    # Extract metadata
    name = re.search(r"Candidate Name\s+(.*)", text)
    community = re.search(r"Community\s+(.*)", text)
    center = re.search(r"Test Center Name\s+(.*)", text)
    test_date = re.search(r"Test Date\s+(.*)", text)
    test_time = re.search(r"Test Time\s+(.*)", text)

    name = name.group(1).strip() if name else "N/A"
    community = community.group(1).strip() if community else "N/A"
    center = center.group(1).strip() if center else "N/A"
    test_date = test_date.group(1).strip() if test_date else "N/A"
    test_time = test_time.group(1).strip() if test_time else "N/A"

    # Extract answers and compute marks
    correct = wrong = unattempted = 0

    question_blocks = text.split("Q.")
    for block in question_blocks:
        status_match = re.search(r"Status\s*:\s*(.*?)\n", block)
        chosen_match = re.search(r"Chosen Option\s*:\s*(.*?)\n", block)
        correct_match = re.search(r"\✓\s*Option\s*(\d)", block)

        if not status_match or not chosen_match:
            continue

        status = status_match.group(1).strip()
        chosen = chosen_match.group(1).strip()

        if status.lower() != "answered" or chosen == "--":
            unattempted += 1
            continue

        correct_option = correct_match.group(1) if correct_match else None

        if chosen == correct_option:
            correct += 1
        else:
            wrong += 1

    total_answered = correct + wrong
    final_mark = round(correct * 1 - wrong * 0.3, 2)

    # Save to CSV
    with open(RESULTS_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), name, community, center, test_date, test_time,
                         category, zone, total_answered, correct, wrong, final_mark])

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

# Run the server on Render-compatible host/port
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
