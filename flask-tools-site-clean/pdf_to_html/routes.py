import os
import uuid
from datetime import datetime
from flask import Blueprint, request, render_template, jsonify, send_from_directory, url_for
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF

pdf_to_html_bp = Blueprint('pdf_to_html', __name__, template_folder='templates',static_folder='static',
    static_url_path='/pdf_to_html/static')

UPLOAD_FOLDER = 'uploads'
CONVERTED_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'converted')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

@pdf_to_html_bp.route('/')
def home():
    return render_template('pdftohtml.html')

@pdf_to_html_bp.route('/start-convert', methods=['POST'])
def start_convert():
    if 'pdf_file' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400

    pdf_file = request.files['pdf_file']
    if not pdf_file or not pdf_file.filename.endswith('.pdf'):
        return jsonify({"success": False, "message": "Only PDF files are allowed."}), 400

    try:
        session_id = str(uuid.uuid4())
        filename = secure_filename(pdf_file.filename)
        upload_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
        pdf_file.save(upload_path)

        # Convert to HTML
        doc = fitz.open(upload_path)
        html_content = ''.join([page.get_text("html") for page in doc])
        html_filename = f"{session_id}.html"
        html_path = os.path.join(CONVERTED_FOLDER, html_filename)

        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@pdf_to_html_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Missing session ID", 400

    html_path = os.path.join(CONVERTED_FOLDER, f"{session_id}.html")
    if not os.path.exists(html_path):
        return "Conversion not completed yet.", 404

    download_link = url_for('pdf_to_html.download_file', filename=f"{session_id}.html")
    return render_template('pdftohtmlsucce.html', download_link=download_link,filename=session_id)
 

@pdf_to_html_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)

@pdf_to_html_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_html_file(filename):
    path = os.path.join(CONVERTED_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"success": True, "message": "File deleted"})
    else:
        return jsonify({"success": False, "message": "File not found"}), 404
