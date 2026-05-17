import os
import uuid
from flask import Blueprint, request, render_template, send_from_directory, redirect, url_for
from PIL import Image

convert_heic_bp = Blueprint('convert_heic', __name__, template_folder='templates')

UPLOAD_FOLDER = 'uploads_heic'
CONVERTED_FOLDER = 'converted_jpg'

# إنشاء المجلدات إذا لم تكن موجودة
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

@convert_heic_bp.route('/')
def home():
    return redirect(url_for('convert_heic.serve_convert_html'))

@convert_heic_bp.route('', methods=['GET'])
def serve_convert_html():
    return render_template('convertheic.html')

@convert_heic_bp.route('/start-convert', methods=['POST'])
def start_convert():
    if 'images' not in request.files:
        return "No images uploaded", 400

    files = request.files.getlist('images')
    if not files:
        return "Please upload at least one image.", 400

    session_id = str(uuid.uuid4())
    converted_files = []

    for file in files:
        if not file.filename.lower().endswith('.heic'):
            continue  # تجاهل الملفات غير HEIC

        original_name = os.path.splitext(file.filename)[0]
        filename = f"{original_name}_{session_id}.jpg"
        filepath = os.path.join(CONVERTED_FOLDER, filename)

        try:
            image = Image.open(file.stream).convert("RGB")
            image.save(filepath, "JPEG")
            converted_files.append(filename)
        except Exception as e:
            return f"Error converting {file.filename}: {str(e)}", 500

    return render_template('convertheic_result.html', converted_files=converted_files)

@convert_heic_bp.route('/converted/<filename>')
def download_converted(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)
