import os
import uuid
from flask import Blueprint, request, render_template, send_from_directory
from PIL import Image

compress_bp = Blueprint('compress', __name__, template_folder='templates')

UPLOAD_FOLDER = 'uploads_compress'
COMPRESSED_FOLDER = 'compressed_images'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESSED_FOLDER, exist_ok=True)

@compress_bp.route('/', methods=['GET'])
def serve_compress_html():
    return render_template('compressimage.html')

@compress_bp.route('/start-compress', methods=['POST'])
def start_compress():
    if 'images' not in request.files:
        return "No images uploaded", 400

    files = request.files.getlist('images')
    if not files:
        return "Please upload at least one image.", 400

    try:
        quality = int(request.form.get('quality', 75))
        if quality < 10 or quality > 95:
            return "Quality must be between 10 and 95.", 400
    except:
        return "Invalid quality value.", 400

    session_id = str(uuid.uuid4())
    compressed_files = []

    for file in files:
        original_name = os.path.splitext(file.filename)[0]
        filename = f"{original_name}_{session_id}.jpg"
        filepath = os.path.join(COMPRESSED_FOLDER, filename)

        try:
            image = Image.open(file.stream).convert("RGB")
            # ضغط الصورة مع ضبط جودة JPG
            image.save(filepath, "JPEG", quality=quality, optimize=True)
            compressed_files.append(filename)
        except Exception as e:
            return f"Error compressing {file.filename}: {str(e)}", 500

    return render_template('compress_result.html', compressed_files=compressed_files)

@compress_bp.route('/compressed/<filename>')
def download_compressed(filename):
    file_path = os.path.join(COMPRESSED_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_from_directory(COMPRESSED_FOLDER, filename, as_attachment=True)
