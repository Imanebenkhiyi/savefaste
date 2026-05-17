import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from werkzeug.utils import secure_filename

delet_page_bp = Blueprint(
    'delet_page',
    __name__,
    static_folder='static',
    static_url_path='/delet_page/static',
    template_folder='templates'
)

UPLOAD_FOLDER = 'uploads'
DELETED_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'deleted')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DELETED_FOLDER, exist_ok=True)

@delet_page_bp.route('/')
def home():
    return redirect(url_for('delet_page.serve_delete_html'))

@delet_page_bp.route('', methods=['GET'])
def serve_delete_html():
    return render_template('deletpage.html')

@delet_page_bp.route('/start-delete', methods=['POST'])
def start_delete():
    if 'pdf' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files['pdf']
    pages_str = request.form.get('pages')
    if not pages_str:
        return jsonify({"success": False, "message": "No page numbers provided"}), 400

    filename = secure_filename(file.filename)
    if not filename.lower().endswith('.pdf'):
        return jsonify({"success": False, "message": "File must be a PDF"}), 400

    session_id = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
    file.save(input_path)

    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()
        total_pages = len(reader.pages)

        try:
            pages_to_delete = {int(p.strip()) - 1 for p in pages_str.split(',')}
        except ValueError:
            return jsonify({"success": False, "message": "Invalid page format"}), 400

        if any(p < 0 or p >= total_pages for p in pages_to_delete):
            return jsonify({"success": False, "message": "One or more pages are out of range"}), 400

        for i in range(total_pages):
            if i not in pages_to_delete:
                writer.add_page(reader.pages[i])

        output_filename = f"{session_id}_deleted.pdf"
        output_path = os.path.join(DELETED_FOLDER, output_filename)
        with open(output_path, 'wb') as f_out:
            writer.write(f_out)

        return jsonify({"success": True, "file": output_filename})
    
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@delet_page_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(DELETED_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_from_directory(DELETED_FOLDER, filename, as_attachment=True)

@delet_page_bp.route('/done')
def done():
    filename = request.args.get('filename')
    if not filename:
        return "Filename not provided", 400
    download_link = url_for('delet_page.download_file', filename=filename)

    return render_template('deletdowland.html', download_link=download_link)

@delet_page_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    path = os.path.join(DELETED_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"success": True, "message": "File deleted"})
    else:
        return jsonify({"success": False, "message": "File not found"}), 404
