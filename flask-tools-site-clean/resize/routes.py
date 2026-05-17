import os
import uuid
from flask import Blueprint, request, render_template, send_from_directory
from PIL import Image

resize_bp = Blueprint('resize', __name__, template_folder='templates')

UPLOAD_FOLDER = 'uploads_resize'
RESIZED_FOLDER = 'resized_images'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESIZED_FOLDER, exist_ok=True)

@resize_bp.route('/', methods=['GET'])
def serve_resize_html():
    return render_template('resizeimage.html')

@resize_bp.route('/start-resize', methods=['POST'])
def start_resize():
    if 'images' not in request.files:
        return "No images uploaded", 400

    files = request.files.getlist('images')
    if not files:
        return "Please upload at least one image.", 400

    try:
        width = int(request.form.get('width'))
        height = int(request.form.get('height'))
        if width <= 0 or height <= 0:
            return "Width and height must be positive integers.", 400
    except:
        return "Invalid width or height.", 400

    session_id = str(uuid.uuid4())
    resized_files = []

    for file in files:
        original_name = os.path.splitext(file.filename)[0]
        filename = f"{original_name}_{session_id}.jpg"
        filepath = os.path.join(RESIZED_FOLDER, filename)

        try:
            image = Image.open(file.stream).convert("RGB")
            resized_img = image.resize((width, height), Image.LANCZOS)
            resized_img.save(filepath, "JPEG")
            resized_files.append(filename)
        except Exception as e:
            return f"Error resizing {file.filename}: {str(e)}", 500

    return render_template('resize_result.html', resized_files=resized_files)

@resize_bp.route('/resized/<filename>')
def download_resized(filename):
    file_path = os.path.join(RESIZED_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_from_directory(RESIZED_FOLDER, filename, as_attachment=True)
