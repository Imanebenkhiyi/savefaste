import os
import uuid
import subprocess
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime

pdf_to_ppt_bp = Blueprint(
    'pdf_to_ppt',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/pdf_to_ppt_static'
)

UPLOAD_FOLDER = 'uploads_pdf2pp'
CONVERTED_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'converted_pdf2ppt'))

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)


@pdf_to_ppt_bp.route('/')
def home():
    return redirect(url_for('pdf_to_ppt.serve_converter_html'))


@pdf_to_ppt_bp.route('', methods=['GET'])
def serve_converter_html():
    return render_template('pdftoppt.html')


@pdf_to_ppt_bp.route('/convert', methods=['POST'])
def convert_pdf_to_ppt():
    if 'pdf' not in request.files:
        return jsonify({"success": False, "message": "No PDF file uploaded."}), 400

    file = request.files['pdf']
    if file.filename == '' or not file.filename.lower().endswith('.pdf'):
        return jsonify({"success": False, "message": "Invalid PDF file."}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    try:
        filename = secure_filename(file.filename)
        input_pdf_path = os.path.join(session_folder, filename)
        file.save(input_pdf_path)

        # ---- FIXED LIBREOFFICE COMMAND ----
        command = [
            'soffice',
            '--headless',
            '--invisible',
            '--norestore',
            '--nolockcheck',
            '--nodefault',
            '--convert-to', 'pptx:impress_png_Export',
            '--outdir', CONVERTED_FOLDER,
            input_pdf_path
        ]

        # Run conversion
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            return jsonify({
                "success": False,
                "message": f"LibreOffice conversion error: {result.stderr.strip()}"
            }), 500
        
        pptx_filename = os.path.splitext(filename)[0] + '.pptx'
        pptx_path = os.path.join(CONVERTED_FOLDER, pptx_filename)

        if not os.path.exists(pptx_path):
            return jsonify({"success": False, "message": "Conversion failed: output file missing."}), 500

        return jsonify({
            "success": True,
            "session_id": session_id,
            "pptx_filename": pptx_filename
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@pdf_to_ppt_bp.route('/progress')
def conversion_progress():
    filename = request.args.get('pptx_filename')
    if not filename:
        return "Missing filename", 400

    file_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return "Conversion not completed yet.", 404

    download_link = url_for('pdf_to_ppt.download_file', filename=filename)

    return render_template('pdftopptsucces.html', download_link=download_link, filename=filename)


@pdf_to_ppt_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return f"❌ File not found: {filename}", 404

    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)


@pdf_to_ppt_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_ppt_file(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)

    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    try:
        os.remove(file_path)
        return jsonify({"success": True, "message": "File deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
