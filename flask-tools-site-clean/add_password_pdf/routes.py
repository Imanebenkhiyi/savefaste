import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from werkzeug.utils import secure_filename
from datetime import datetime

add_password_pdf_bp = Blueprint('add_password_pdf', __name__, template_folder='templates')

UPLOAD_FOLDER = 'uploads_password'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ENCRYPTED_FOLDER = os.path.join(BASE_DIR, 'encrypted')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENCRYPTED_FOLDER, exist_ok=True)

@add_password_pdf_bp.route('/')
def home():
    return redirect(url_for('add_password_pdf.serve_password_html'))

@add_password_pdf_bp.route('', methods=['GET'])
def serve_password_html():
    return render_template('addpassword.html')  # تأكد من وجود هذا القالب

@add_password_pdf_bp.route('/start-encrypt', methods=['POST'])
def start_encrypt():
    if 'pdf_file' not in request.files:
        return jsonify({"success": False, "message": "No PDF file uploaded"}), 400

    file = request.files['pdf_file']
    password = request.form.get('password', '').strip()

    if not file or file.filename == '':
        return jsonify({"success": False, "message": "No PDF file selected"}), 400
    if not password:
        return jsonify({"success": False, "message": "Password is required"}), 400
    if file.content_type != 'application/pdf':
        return jsonify({"success": False, "message": "Invalid file type. Please upload a PDF."}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    original_path = os.path.join(session_folder, filename)
    file.save(original_path)

    try:
        reader = PdfReader(original_path)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.encrypt(password)

        encrypted_filename = f"{session_id}.pdf"
        encrypted_path = os.path.join(ENCRYPTED_FOLDER, encrypted_filename)
        with open(encrypted_path, 'wb') as f_out:
            writer.write(f_out)

        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@add_password_pdf_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Missing session ID", 400

    encrypted_path = os.path.join(ENCRYPTED_FOLDER, f"{session_id}.pdf")
    if not os.path.exists(encrypted_path):
        return "Encryption not completed yet.", 404

    download_link = url_for('add_password_pdf.download_file', filename=f"{session_id}.pdf")
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>PDF Encryption Success</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>
  <style>
    body {{
      margin: 0; padding: 0;
      background: linear-gradient(135deg, #ffe0e0, #fff1f1);
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      min-height: 100vh; display: flex;
      justify-content: center; align-items: center;
    }}
    .container {{
      background-color: #fff;
      border-radius: 20px;
      padding: 50px 40px;
      max-width: 700px;
      box-shadow: 0 8px 30px rgba(0,0,0,0.1);
      text-align: center;
    }}
    .header h1 {{
      font-size: 2.4rem; color: #c0392b; margin-bottom: 10px;
    }}
    .header p {{
      color: #555; font-size: 1rem; margin-bottom: 25px;
    }}
    .success-icon {{
      color: #e74c3c;
      font-size: 4rem;
      margin-bottom: 25px;
    }}
    .file-info {{
      background-color: #f8d7da;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 30px;
      box-shadow: inset 0 1px 3px rgba(0,0,0,0.05);
    }}
    .file-info p {{
      font-size: 1rem;
      color: #721c24;
      margin: 10px 0;
    }}
    .buttons {{
      display: flex;
      gap: 20px;
      justify-content: center;
      flex-wrap: wrap;
    }}
    .btn {{
      padding: 14px 24px;
      font-size: 1rem;
      border-radius: 10px;
      font-weight: bold;
      text-decoration: none;
      box-shadow: 0 2px 10px rgba(0,0,0,0.1);
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: white;
      transition: background-color 0.3s ease;
    }}
    .btn-download {{
      background-color: #c0392b;
    }}
    .btn-download:hover {{
      background-color: #922b21;
    }}
    .btn-new {{
      background-color: #7f8c8d;
    }}
    .btn-new:hover {{
      background-color: #636e72;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🔒 PDF Encrypted Successfully!</h1>
      <p>Your PDF is now password protected.</p>
    </div>

    <div class="success-icon">
      <i class="fa-solid fa-lock"></i>
    </div>

    <div class="file-info">
      <p><strong>📄 File Name:</strong> {session_id}.pdf</p>
      <p><strong>⏱ Created At:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="buttons">
      <a href="{download_link}" class="btn btn-download" download>
        <i class="fa-solid fa-download"></i> Download Encrypted PDF
      </a>
      <a href="/addpassword" class="btn btn-new">
        <i class="fa-solid fa-file-circle-plus"></i> Encrypt New PDF
      </a>
    </div>
  </div>
</body>
</html>
"""

@add_password_pdf_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(ENCRYPTED_FOLDER, filename)
    print(">> Full path:", file_path)
    print(">> Exists:", os.path.exists(file_path))
    print(">> Files in encrypted folder:", os.listdir(ENCRYPTED_FOLDER))

    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(ENCRYPTED_FOLDER, filename, as_attachment=True)
