import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from werkzeug.utils import secure_filename
from datetime import datetime

rotate_page_bp = Blueprint('rotate_page', __name__, template_folder='templates',static_folder='static',
    static_url_path='/rotate_page/static')

UPLOAD_FOLDER = 'uploads'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROTATED_FOLDER = os.path.join(BASE_DIR, 'rotated')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ROTATED_FOLDER, exist_ok=True)

@rotate_page_bp.route('/')
def home():
    return redirect(url_for('rotate_page.serve_rotate_html'))

@rotate_page_bp.route('', methods=['GET'])
def serve_rotate_html():
    return render_template('rotatepage.html')

@rotate_page_bp.route('/start-rotate', methods=['POST'])
def start_rotate():
    if 'pdf' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files['pdf']
    degrees = int(request.form.get('degrees', 90))

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    filepath = os.path.join(session_folder, filename)
    file.save(filepath)

    try:
        reader = PdfReader(filepath)
        writer = PdfWriter()

        for page in reader.pages:
            page.rotate(degrees)
            writer.add_page(page)

        rotated_filename = f"{session_id}.pdf"
        rotated_path = os.path.join(ROTATED_FOLDER, rotated_filename)

        with open(rotated_path, "wb") as f_out:
            writer.write(f_out)

        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@rotate_page_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Missing session ID", 400

    rotated_path = os.path.join(ROTATED_FOLDER, f"{session_id}.pdf")
    if not os.path.exists(rotated_path):
        return "Rotation not completed yet.", 404

    download_link = url_for('rotate_page.download_file', filename=f"{session_id}.pdf")
    filename = f"{session_id}.pdf"
    return render_template('rotatedowland.html', download_link=download_link, filename=filename)


@rotate_page_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(ROTATED_FOLDER, filename)
    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(ROTATED_FOLDER, filename, as_attachment=True) 


@rotate_page_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    path = os.path.join(ROTATED_FOLDER , filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"success": True, "message": "File deleted"})
    else:
        return jsonify({"success": False, "message": "File not found"}), 404