import os
import uuid
import subprocess
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime

excel_to_pdf_bp = Blueprint('excel_to_pdf', __name__, template_folder='templates',static_folder='static',
    static_url_path='/pdf_to_word/static')

UPLOAD_FOLDER = 'uploads_excel'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONVERTED_FOLDER = os.path.join(BASE_DIR, 'converted_pdfs')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

def convert_xlsx_to_pdf(input_path, output_dir):
    # أمر تحويل Excel إلى PDF باستخدام LibreOffice في الوضع الخفي (بدون واجهة)
    result = subprocess.run([
        'libreoffice',
        '--headless',
        '--convert-to', 'pdf',
        input_path,
        '--outdir', output_dir
    ], capture_output=True)

    if result.returncode != 0:
        raise Exception(f"LibreOffice conversion failed: {result.stderr.decode()}")

    output_pdf = os.path.splitext(os.path.basename(input_path))[0] + '.pdf'
    return os.path.join(output_dir, output_pdf)

@excel_to_pdf_bp.route('/')
def home():
    return redirect(url_for('excel_to_pdf.serve_convert_html'))

@excel_to_pdf_bp.route('', methods=['GET'])
def serve_convert_html():
    return render_template('exceltopdf.html')

@excel_to_pdf_bp.route('/start-convert', methods=['POST'])
def start_convert():
    if 'excels' not in request.files:
        return jsonify({"success": False, "message": "No files uploaded"}), 400

    files = request.files.getlist('excels')
    if len(files) < 1:
        return jsonify({"success": False, "message": "Please upload at least one Excel file."}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    converted_files = []

    try:
        for file in files:
            filename = secure_filename(file.filename)
            filepath = os.path.join(session_folder, filename)
            file.save(filepath)

            output_pdf_path = convert_xlsx_to_pdf(filepath, CONVERTED_FOLDER)
            converted_files.append(os.path.basename(output_pdf_path))

        return jsonify({"success": True, "session_id": session_id, "files": converted_files})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@excel_to_pdf_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    filename = request.args.get('filename')

    if not session_id:
        return "Missing session ID", 400

    if not filename:
        # رسالة تفيد أن التحويل جاري ولا يوجد ملف جاهز للتحميل بعد
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><title>Conversion In Progress</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
          <h2>⏳ Conversion in Progress</h2>
          <p>The file is still being processed. Please wait a moment and refresh this page.</p>
        </body>
        </html>
        """, 202

    converted_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(converted_path):
        return "Conversion not completed yet.", 404

    download_link = url_for('excel_to_pdf.download_file', filename=filename)
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Conversion Complete</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>
  <style>
    body {{
      background: linear-gradient(135deg, #e0f7fa, #f1f8ff);
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }}
    .container {{
      background: white;
      border-radius: 20px;
      padding: 50px;
      text-align: center;
      box-shadow: 0 8px 30px rgba(0,0,0,0.1);
    }}
    h1 {{ color: green; }}
    .btn {{
      margin-top: 20px;
      padding: 10px 20px;
      border: none;
      border-radius: 8px;
      background-color: #007bff;
      color: white;
      text-decoration: none;
      font-weight: bold;
      display: inline-block;
    }}
    .btn:hover {{ background-color: #0056b3; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>✅ Excel Converted to PDF Successfully!</h1>
    <p><strong>Filename:</strong> {filename}</p>
    <p><strong>Generated At:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    <a href="{download_link}" class="btn" download><i class="fa fa-download"></i> Download PDF</a>
  </div>
</body>
</html>
"""


@excel_to_pdf_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return f"❌ File not found at: {file_path}", 404
    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)
