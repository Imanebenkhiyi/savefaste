import os
import uuid
import subprocess
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from werkzeug.utils import secure_filename

word_to_pdf_bp = Blueprint( 'word_to_pdf', __name__, template_folder='templates',  static_folder='static')

UPLOAD_FOLDER = 'uploads'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONVERTED_FOLDER = os.path.join(BASE_DIR, 'converted')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

# Local sessions like merge PDF
local_sessions_word = {}

@word_to_pdf_bp.route('/')
def home():
    return redirect(url_for('word_to_pdf.serve_convert_html'))

@word_to_pdf_bp.route('', methods=['GET'])
def serve_convert_html():
    return render_template('wordtopdf.html')


@word_to_pdf_bp.route('/start-convert', methods=['POST'])
def start_convert():
    if 'words' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files['words']
    if file.filename == '':
        return jsonify({"success": False, "message": "Please select a file"}), 400

    if not file.filename.lower().endswith('.docx'):
        return jsonify({"success": False, "message": "Only .docx files are supported"}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    filepath = os.path.join(session_folder, filename)
    file.save(filepath)

    original_name = os.path.splitext(filename)[0]  # بدون .docx
    pdf_final_name = f"{original_name}.pdf"

    # Save local session
    local_sessions_word[session_id] = {
        "status": "processing",
        "progress": 10,
        "message": "Converting Word to PDF...",
        "original_name": original_name
    }

    try:
        # Convert using LibreOffice
        subprocess.run([
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', CONVERTED_FOLDER,
            filepath
        ], check=True)

        generated_pdf_path = os.path.join(CONVERTED_FOLDER, pdf_final_name)

        if not os.path.exists(generated_pdf_path):
            return jsonify({"success": False, "message": "Conversion failed: PDF file not created"}), 500

        local_sessions_word[session_id]["status"] = "done"
        local_sessions_word[session_id]["progress"] = 100
        local_sessions_word[session_id]["message"] = "Conversion completed successfully"
        local_sessions_word[session_id]["converted_filename"] = pdf_final_name

        return jsonify({"success": True, "session_id": session_id})

    except Exception as e:
        local_sessions_word[session_id]["status"] = "error"
        local_sessions_word[session_id]["message"] = str(e)
        return jsonify({"success": False, "message": str(e)}), 500


@word_to_pdf_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"success": False, "message": "Missing session_id"}), 400

    # ✔ التصحيح هنا: نستخدم local_sessions_word
    session = local_sessions_word.get(session_id)
    if not session:
        return jsonify({"success": False, "message": "Session not found"}), 404

    # ✔ إذا التحويل لم يكتمل
    if session["status"] != "done":
        return jsonify({
            "success": True,
            "status": session["status"],
            "progress": session["progress"],
            "message": session["message"],
            "converted_filename": None
        })

    # ✔ إذا التحويل انتهى
    converted_filename = session.get("converted_filename")
    if not converted_filename:
        return jsonify({"success": False, "message": "Converted file missing"}), 500

    download_link = url_for('word_to_pdf.download_file', filename=converted_filename)

    return render_template("wordtopdfsucces.html",
                           filename=converted_filename,
                           download_link=download_link)

@word_to_pdf_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(CONVERTED_FOLDER, filename, as_attachment=True)

@word_to_pdf_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_wordpdf(filename):
    file_path = os.path.join(CONVERTED_FOLDER, filename)

    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "File not found"}), 404

    try:
        os.remove(file_path)
        return jsonify({"success": True, "message": "File deleted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
