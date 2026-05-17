import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from PIL import Image
from werkzeug.utils import secure_filename
from datetime import datetime

image_to_pdf_bp = Blueprint('image_to_pdf', __name__, template_folder='templates')

UPLOAD_FOLDER = 'uploads_images'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PDF_FOLDER = os.path.join(BASE_DIR, 'pdfs_converted')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

@image_to_pdf_bp.route('/')
def home():
    return redirect(url_for('image_to_pdf.serve_upload_html'))

@image_to_pdf_bp.route('', methods=['GET'])
def serve_upload_html():
    return render_template('imagetopdf.html')

@image_to_pdf_bp.route('/start-convert', methods=['POST'])
def start_convert():
    if 'images' not in request.files:
        return jsonify({"success": False, "message": "No files uploaded"}), 400

    files = request.files.getlist('images')
    if len(files) == 0:
        return jsonify({"success": False, "message": "Please upload at least one image file."}), 400

    # تحقق من نوع الملفات (اختياري)
    allowed_types = {'image/jpeg', 'image/png', 'image/jpg', 'image/bmp', 'image/gif'}
    for file in files:
        if file.content_type not in allowed_types:
            return jsonify({"success": False, "message": f"Unsupported file type: {file.filename}"}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    image_paths = []
    try:
        for file in files:
            filename = secure_filename(file.filename)
            filepath = os.path.join(session_folder, filename)
            file.save(filepath)
            image_paths.append(filepath)

        # تحويل الصور إلى PDF
        images = []
        for path in image_paths:
            img = Image.open(path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)

        pdf_filename = f"{session_id}.pdf"
        pdf_path = os.path.join(PDF_FOLDER, pdf_filename)

        # حفظ أول صورة كـ PDF ثم إرفاق الباقي
        images[0].save(pdf_path, save_all=True, append_images=images[1:])

        return jsonify({"success": True, "session_id": session_id})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@image_to_pdf_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Missing session ID", 400

    pdf_path = os.path.join(PDF_FOLDER, f"{session_id}.pdf")
    if not os.path.exists(pdf_path):
        return "Conversion not completed yet.", 404

    download_link = url_for('image_to_pdf.download_file', filename=f"{session_id}.pdf")
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Image to PDF Conversion Success</title>
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
      <h1>🎉 Conversion Successful!</h1>
      <p>Your PDF document is ready to download.</p>
    </div>

    <div class="success-icon">
      <i class="fa-solid fa-circle-check"></i>
    </div>

    <div class="file-info">
      <p><strong>📄 File Name:</strong> {session_id}.pdf</p>
      <p><strong>📦 Estimated Size:</strong> ~1-5 MB</p>
      <p><strong>⏱ Created At:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="buttons">
      <a href="{download_link}" class="btn btn-download" download>
        <i class="fa-solid fa-download"></i> Download PDF
      </a>
      <a href="/imagetopdf" class="btn btn-new">
        <i class="fa-solid fa-file-circle-plus"></i> Convert New Images
      </a>
    </div>
  </div>
</body>
</html>
"""

@image_to_pdf_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(PDF_FOLDER, filename)
    print(">> Full path:", file_path)
    print(">> Exists:", os.path.exists(file_path))
    print(">> Files in PDF folder:", os.listdir(PDF_FOLDER))

    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(PDF_FOLDER, filename, as_attachment=True)
