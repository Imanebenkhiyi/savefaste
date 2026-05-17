import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime
from pdf2docx import Converter

pdf_to_word_bp = Blueprint('pdf_to_word', __name__, template_folder='templates',static_folder='static',
    static_url_path='/pdf_to_word/static',)

UPLOAD_FOLDER = 'uploads'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONVERTED_FOLDER = os.path.join(BASE_DIR, 'converted')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

@pdf_to_word_bp.route('/')
def home():
    return redirect(url_for('pdf_to_word.serve_convert_html'))

@pdf_to_word_bp.route('', methods=['GET'])
def serve_convert_html():
    return render_template('pdftoword.html')

@pdf_to_word_bp.route('/start-convert', methods=['POST'])
def start_convert():
    if 'pdf' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files['pdf']
    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    pdf_path = os.path.join(session_folder, filename)
    file.save(pdf_path)

    try:
        word_filename = f"{session_id}.docx"
        word_path = os.path.join(CONVERTED_FOLDER, word_filename)

        converter = Converter(pdf_path)
        converter.convert(word_path, start=0, end=None)
        converter.close()

        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@pdf_to_word_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Missing session ID", 400

    converted_path = os.path.join(CONVERTED_FOLDER, f"{session_id}.docx")
    if not os.path.exists(converted_path):
        return "Conversion not completed yet.", 404

    download_link = url_for('pdf_to_word.download_file', filename=f"{session_id}.docx")
    return render_template('pdf_to_word_success.html', download_link=download_link,filename=session_id)


@pdf_to_word_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)

@pdf_to_word_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_word_file(filename):
    path = os.path.join(CONVERTED_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"success": True, "message": "File deleted"})
    else:
        return jsonify({"success": False, "message": "File not found"}), 404
