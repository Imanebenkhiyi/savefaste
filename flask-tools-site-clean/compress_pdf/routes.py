import os
from flask import Blueprint, request, render_template, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
import uuid
import subprocess

compress_pdf_bp = Blueprint(
    'compress_pdf',
    __name__,
    static_folder='static',
    static_url_path='/compress_pdf/static',
    template_folder='templates'
)

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
COMPRESS_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'compressed_files')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPRESS_FOLDER, exist_ok=True)

@compress_pdf_bp.route('/')
def home():
    return redirect(url_for('compress_pdf.compress_home'))

@compress_pdf_bp.route('', methods=['GET'])
def compress_home():
    return render_template('compresspdf.html')

@compress_pdf_bp.route('/start-compress', methods=['POST'])
def start_compress():
    if 'pdf' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files['pdf']
    filename = secure_filename(file.filename)
    if not filename.lower().endswith('.pdf'):
        return jsonify({"success": False, "message": "Invalid PDF file"}), 400

    session_id = str(uuid.uuid4())
    saved_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
    file.save(saved_path)

    output_filename = f"{session_id}_compressed.pdf"
    output_path = os.path.join(COMPRESS_FOLDER, output_filename)

    try:
        command = [
            'gs',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/ebook',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            f'-sOutputFile={output_path}',
            saved_path
        ]

        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print("Ghostscript error:", result.stderr)
            return jsonify({"success": False, "message": "Compression failed", "error": result.stderr}), 500

        download_url = url_for('compress_pdf.done', filename=output_filename)
        return jsonify({"success": True, "file": output_filename, "download_url": download_url})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@compress_pdf_bp.route('/download/<filename>')
def download_file(filename):
    path = os.path.join(COMPRESS_FOLDER, filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_from_directory(COMPRESS_FOLDER, filename, as_attachment=True)

@compress_pdf_bp.route('/done')
def done():
    filename = request.args.get('filename')
    if not filename:
        return "Missing file name", 400
    download_link = url_for('compress_pdf.download_file', filename=filename)
    return render_template('dowland.html', download_link=download_link)

@compress_pdf_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    path = os.path.join(COMPRESS_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"success": True, "message": "File deleted"})
    else:
        return jsonify({"success": False, "message": "File not found"}), 404
