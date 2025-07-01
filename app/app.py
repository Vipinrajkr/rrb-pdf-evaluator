from flask import Flask, request, jsonify, render_template
app = Flask(__name__)
CORS(app)
import fitz  # PyMuPDF
import csv
import os
import re
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
RESULTS_CSV = "results.csv"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Simple RRB zone list for dropdown (can be expanded)
RRB_ZONES = ["Ahmedabad", "Ajmer", "Allahabad", "Bangalore", "Bhopal", "Bhubaneswar", "Bilaspur", "Chandigarh",
             "Chennai", "Gorakhpur", "Guwahati", "Jammu", "Kolkata", "Malda", "Mumbai", "Muzaffarpur", "Patna",
             "Ranchi", "Secunderabad", "Siliguri", "Thiruvananthapuram"]

@app.route('/')
def index():
    return render_template('index.html', zones=RRB_ZONES)

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

    questions = re.findall(r'Q\.(\d+).*?Status\s*:\s*(.*?)\nChosen Option\s*:\s*(.*?)\n', text, re.DOTALL)
    correct = wrong = unattempted = 0

    for match in re.finditer(r"Status\s*:\s*(.*?)\nChosen Option\s*:\s*(.*?)\n", text):
        status = match.group(1).strip()
        chosen = match.group(2).strip()
        correct_line = text[match.start():match.end()+300]
        correct_option = None

        # Extract correct option from text (basic version without colors/tick icons)
        # A more robust version would require analyzing PDF blocks directly

        correct_match = re.search(r"\u2713\)?\s*Option\s(\d)\s", correct_line)
        if correct_match:
            correct_option = correct_match.group(1)

        if status.lower() != "answered" or chosen == "--":
            unattempted += 1
        elif correct_option == chosen:
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

