import os
import uuid
import subprocess
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime

pdf_to_ppt_bp = Blueprint('pdf_to_ppt', __name__, template_folder='templates')

UPLOAD_FOLDER = 'uploads_pdf2pp'
CONVERTED_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'converted_pdf2ppt'))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

@pdf_to_ppt_bp.route('/')
def home():
    return redirect(url_for('pdf_to_ppt.serve_converter_html'))

@pdf_to_ppt_bp.route('', methods=['GET'])
def serve_converter_html():
    return render_template('pdftoppt.html')
@pdf_to_ppt_bp.route('/convert', methods=['POST'])
def convert_pdf_to_ppt():
    if 'pdf' not in request.files:
        return jsonify({"success": False, "message": "No PDF file uploaded."}), 400

    file = request.files['pdf']
    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({"success": False, "message": "Invalid PDF file."}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    try:
        filename = secure_filename(file.filename)
        input_pdf_path = os.path.join(session_folder, filename)
        file.save(input_pdf_path)

        command = [
            'libreoffice',
            '--headless',
            '--convert-to', 'pptx',
            '--outdir', CONVERTED_FOLDER,
            input_pdf_path
        ]

        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify({
                "success": False,
                "message": f"LibreOffice conversion error: {result.stderr.strip()}"
            }), 500

        pptx_filename = os.path.splitext(filename)[0] + '.pptx'
        pptx_path = os.path.join(CONVERTED_FOLDER, pptx_filename)

        if not os.path.exists(pptx_path):
            return jsonify({"success": False, "message": "Conversion failed: output file missing."}), 500

        return jsonify({"success": True, "session_id": session_id, "pptx_filename": pptx_filename})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@pdf_to_ppt_bp.route('/progress')
def conversion_progress():
    filename = request.args.get('pptx_filename')
    if not filename:
        return "Missing filename", 400

    file_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return "Conversion not completed yet.", 404

    download_link = url_for('pdf_to_ppt.download_file', filename=filename)

    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>PDF to PPTX Success</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: linear-gradient(135deg, #fff3e0, #ffebee);
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
    .header h1 {{
      font-size: 2.4rem;
      color: #333;
    }}
    .success-icon {{
      color: #17a2b8;
      font-size: 4rem;
      margin: 20px 0;
    }}
    .file-info {{
      background-color: #f1f1f1;
      border-radius: 12px;
      padding: 20px;
      width: 100%;
      text-align: left;
    }}
    .buttons {{
      display: flex;
      gap: 20px;
      margin-top: 20px;
      flex-wrap: wrap;
      justify-content: center;
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
    }}
    .btn-download {{
      background-color: #17a2b8;
      color: white;
    }}
    .btn-download:hover {{
      background-color: #117a8b;
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
      <h1>✅ PDF Converted to PPTX!</h1>
    </div>

    <div class="success-icon">
      <i class="fa-solid fa-file-powerpoint"></i>
    </div>

    <div class="file-info">
      <p><strong>🎯 File Name:</strong> {filename}</p>
      <p><strong>📅 Converted At:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="buttons">
      <a href="{download_link}" class="btn btn-download" download>
        <i class="fa-solid fa-download"></i> Download PPTX
      </a>
      <a href="/pdf-to-ppt" class="btn btn-new">
        <i class="fa-solid fa-file-arrow-up"></i> Convert Another PDF
      </a>
    </div>
  </div>
</body>
</html>
"""

@pdf_to_ppt_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return f"❌ File not found: {filename}", 404
    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)
