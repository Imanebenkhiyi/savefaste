
import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from PyPDF2 import PdfMerger
from werkzeug.utils import secure_filename
from datetime import datetime

merge_pdf_bp = Blueprint('merge_pdf', __name__, template_folder='templates')

UPLOAD_FOLDER = 'uploads'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
MERGED_FOLDER = os.path.join(BASE_DIR, 'merged')


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MERGED_FOLDER, exist_ok=True)

@merge_pdf_bp.route('/')
def home():
    return redirect(url_for('merge_pdf.serve_merge_html'))

@merge_pdf_bp.route('', methods=['GET'])
def serve_merge_html():
    return render_template('mergepdf.html')

@merge_pdf_bp.route('/start-merge', methods=['POST'])
def start_merge():
    if 'pdfs' not in request.files:
        return jsonify({"success": False, "message": "No files uploaded"}), 400

    files = request.files.getlist('pdfs')
    if len(files) < 2:
        return jsonify({"success": False, "message": "Please upload at least two PDF files."}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    merger = PdfMerger()
    try:
        for file in files:
            filename = secure_filename(file.filename)
            filepath = os.path.join(session_folder, filename)
            file.save(filepath)
            merger.append(filepath)

        merged_filename = f"{session_id}.pdf"
        merged_path = os.path.join(MERGED_FOLDER, merged_filename)
        merger.write(merged_path)
        merger.close()

        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@merge_pdf_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Missing session ID", 400

    merged_path = os.path.join(MERGED_FOLDER, f"{session_id}.pdf")
    if not os.path.exists(merged_path):
        return "Merge not completed yet.", 404

    download_link = url_for('merge_pdf.download_file', filename=f"{session_id}.pdf")
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>PDF Merge Success</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: linear-gradient(135deg, #e0f7fa, #f1f8ff);
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
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
    }}
    .header {{
      width: 100%;
      text-align: center;
      margin-bottom: 25px;
    }}
    .header h1 {{
      font-size: 2.4rem;
      color: #333;
      margin-bottom: 10px;
    }}
    .header p {{
      color: #555;
      font-size: 1rem;
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
      text-align: left;
      margin-bottom: 30px;
      box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
    }}
    .file-info p {{
      margin: 10px 0;
      font-size: 1rem;
      color: #444;
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
      <h1>🎉 PDF Merged Successfully!</h1>
      <p>Your document is now ready to download and use.</p>
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
      <a href="/mergepdf" class="btn btn-new">
        <i class="fa-solid fa-file-circle-plus"></i> Merge New Files
      </a>
    </div>
  </div>
</body>
</html>
"""

@merge_pdf_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(MERGED_FOLDER, filename)
    print(">> Full path:", file_path)
    print(">> Exists:", os.path.exists(file_path))
    print(">> Files in merged folder:", os.listdir(MERGED_FOLDER))

    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(MERGED_FOLDER, filename, as_attachment=True) 