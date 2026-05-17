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

        images = []
        for path in image_paths:
            img = Image.open(path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)

        pdf_filename = f"{session_id}.pdf"
        pdf_path = os.path.join(PDF_FOLDER, pdf_filename)

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

    return render_template("imagetopdfsucces.html",
                           filename=f"{session_id}.pdf",
                           download_link=download_link)


@image_to_pdf_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(PDF_FOLDER, filename)

    if not os.path.exists(file_path):
        return f"❌ File not found: {filename}", 404

    return send_from_directory(PDF_FOLDER, filename, as_attachment=True)


# 🟢 مسار الحذف الخاص بـ image_to_pdf فقط
@image_to_pdf_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_pdf_file(filename):
    file_path = os.path.join(PDF_FOLDER, filename)

    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    try:
        os.remove(file_path)
        return jsonify({"success": True, "message": "File deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
