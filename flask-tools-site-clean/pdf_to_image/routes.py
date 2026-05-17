import os
import uuid
import zipfile
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename
from datetime import datetime
import shutil

pdf_to_image_bp = Blueprint('pdf_to_image', __name__, template_folder='templates',static_folder='static',
    static_url_path='/pdf_to_image/static')

UPLOAD_FOLDER = 'uploads'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'converted_images')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@pdf_to_image_bp.route('/')
def home():
    return redirect(url_for('pdf_to_image.serve_pdf_to_image_html'))

@pdf_to_image_bp.route('', methods=['GET'])
def serve_pdf_to_image_html():
    return render_template('pdftoimage.html')

@pdf_to_image_bp.route('/start-convert', methods=['POST'])
def start_convert():
    if 'pdf_file' not in request.files:
        return jsonify({"success": False, "message": "No PDF uploaded"}), 400

    file = request.files['pdf_file']
    filename = secure_filename(file.filename)
    session_id = str(uuid.uuid4())

    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    pdf_path = os.path.join(session_folder, filename)
    file.save(pdf_path)

    try:
        images = convert_from_path(pdf_path)
        image_paths = []

        for idx, img in enumerate(images):
            image_filename = f"page_{idx+1}.jpg"
            img_path = os.path.join(output_folder, image_filename)
            img.save(img_path, "JPEG")
            image_paths.append(img_path)

        # Create a zip of all images
        zip_filename = f"{session_id}.zip"
        zip_path = os.path.join(OUTPUT_FOLDER, zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for img_path in image_paths:
                zipf.write(img_path, arcname=os.path.basename(img_path))

        return jsonify({"success": True, "session_id": session_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@pdf_to_image_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Missing session ID", 400

    zip_path = os.path.join(OUTPUT_FOLDER, f"{session_id}.zip")
    if not os.path.exists(zip_path):
        return "Conversion not completed yet.", 404

    download_link = url_for('pdf_to_image.download_file', filename=f"{session_id}.zip")
    return render_template('pdftoimagesucce.html', download_link=download_link,filename=session_id)

@pdf_to_image_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    print(">> Full path:", file_path)
    print(">> Exists:", os.path.exists(file_path))
    print(">> Files in output folder:", os.listdir(OUTPUT_FOLDER))

    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

@pdf_to_image_bp.route('/delete/<session_id>', methods=['DELETE'])
def delete_image_session(session_id):
    output_folder = os.path.join(OUTPUT_FOLDER, session_id)
    zip_file = os.path.join(OUTPUT_FOLDER, f"{session_id}.zip")
    upload_folder = os.path.join(UPLOAD_FOLDER, session_id)

    try:
        # حذف مجلد الصور المستخرجة
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)

        # حذف ملف zip
        if os.path.exists(zip_file):
            os.remove(zip_file)

        # حذف مجلد التحميل المؤقت
        if os.path.exists(upload_folder):
            shutil.rmtree(upload_folder)

        return jsonify({"success": True, "message": "Session deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

