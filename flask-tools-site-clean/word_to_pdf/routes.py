import os
import uuid
import subprocess
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime

word_to_pdf_bp = Blueprint('word_to_pdf', __name__, template_folder='templates')

UPLOAD_FOLDER = 'uploads'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONVERTED_FOLDER = os.path.join(BASE_DIR, 'converted')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)


@word_to_pdf_bp.route('/')
def home():
    return redirect(url_for('word_to_pdf.serve_convert_html'))

@word_to_pdf_bp.route('', methods=['GET'])
def serve_convert_html():
    return render_template('wordtopdf.html')  # HTML page to upload Word files

@word_to_pdf_bp.route('/start-convert', methods=['POST'])
def start_convert():
    if 'words' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files['words']
    if file.filename == '':
        return jsonify({"success": False, "message": "Please select a file"}), 400

    if not file.filename.lower().endswith('.docx'):
        return jsonify({"success": False, "message": "Only .docx files are supported"}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    filepath = os.path.join(session_folder, filename)
    file.save(filepath)

    try:
        # تحويل الملف باستخدام LibreOffice
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', CONVERTED_FOLDER,
            filepath
        ], check=True)

        # اسم الملف الناتج سيكون نفسه ولكن بامتداد .pdf
        pdf_filename = os.path.splitext(filename)[0] + '.pdf'
        generated_pdf_path = os.path.join(CONVERTED_FOLDER, pdf_filename)
        final_pdf_path = os.path.join(CONVERTED_FOLDER, f"{session_id}.pdf")

        os.rename(generated_pdf_path, final_pdf_path)

        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@word_to_pdf_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Session ID is missing", 400

    converted_path = os.path.join(CONVERTED_FOLDER, f"{session_id}.pdf")
    if not os.path.exists(converted_path):
        return "Conversion not completed yet.", 404

    download_link = url_for('word_to_pdf.download_file', filename=f"{session_id}.pdf")
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Conversion Successful</title>
  <style>
    body {{
      margin: 0; padding: 0; background: linear-gradient(135deg, #e0f7fa, #f1f8ff);
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      min-height: 100vh; display: flex; justify-content: center; align-items: center;
    }}
    .container {{
      background-color: #ffffff;
      border-radius: 20px;
      padding: 50px 40px;
      width: 95%;
      max-width: 700px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.1);
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
    }}
    .header h1 {{
      font-size: 2.4rem;
      color: #333;
      margin-bottom: 10px;
    }}
    .header p {{
      color: #555;
      font-size: 1rem;
      margin-bottom: 25px;
    }}
    .success-icon {{
      color: #28a745;
      font-size: 4rem;
      margin-bottom: 25px;
    }}
    .file-info {{
      background-color: #f8f9fa;
      border-radius: 12px;
      padding: 20px;
      width: 100%;
      margin-bottom: 30px;
      box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
      text-align: left;
      color: #444;
      font-size: 1rem;
    }}
    .buttons {{
      display: flex;
      gap: 20px;
      flex-wrap: wrap;
      justify-content: center;
      margin-top: 10px;
    }}
    .btn {{
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 14px 24px;
      font-size: 1rem;
      border-radius: 10px;
      text-decoration: none;
      font-weight: bold;
      transition: all 0.3s ease;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }}
    .btn-download {{
      background-color: #007bff;
      color: white;
    }}
    .btn-download:hover {{
      background-color: #0056b3;
    }}
    .btn-new {{
      background-color: #6c757d;
      color: white;
    }}
    .btn-new:hover {{
      background-color: #495057;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🎉 Word File Converted Successfully!</h1>
      <p>Your document is ready to download.</p>
    </div>

    <div class="success-icon">
      <i class="fa-solid fa-circle-check"></i>
    </div>

    <div class="file-info">
      <p><strong>📄 File Name:</strong> {session_id}.pdf</p>
      <p><strong>📦 Estimated Size:</strong> ~1-3 MB</p>
      <p><strong>⏱ Created At:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="buttons">
      <a href="{download_link}" class="btn btn-download" download>
        <i class="fa-solid fa-download"></i> Download PDF
      </a>
      <a href="/" class="btn btn-new">
        <i class="fa-solid fa-file-circle-plus"></i> Convert New File
      </a>
    </div>
  </div>
</body>
</html>
"""

@word_to_pdf_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)
