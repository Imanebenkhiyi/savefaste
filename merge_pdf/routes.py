# merge_pdf_bp.py - PDF merge with progress, no Firebase, no usage limits
import os
import uuid
from functools import wraps
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for, make_response
from PyPDF2 import PdfMerger, PdfReader
from werkzeug.utils import secure_filename
from datetime import datetime

# ---- Config ----
merge_pdf_bp = Blueprint('merge_pdf', __name__, template_folder='templates')

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
MERGED_FOLDER = os.path.join(BASE_DIR, 'merged')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MERGED_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'.pdf'}
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB per file
MAX_FILES = 20

# ---- Local sessions for progress tracking ----
local_sessions = {}

# ---- Helpers ----
def allowed_file(filename):
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS

def create_session(session_id):
    local_sessions[session_id] = {"status": "created", "progress": 0, "message": "Created"}

def update_session(session_id, status=None, progress=None, message=None, merged_filename=None):
    session = local_sessions.get(session_id, {})
    if status: session['status'] = status
    if progress is not None: session['progress'] = progress
    if message: session['message'] = message
    if merged_filename: session['merged_filename'] = merged_filename
    local_sessions[session_id] = session

# ---- Routes ----
@merge_pdf_bp.route('/')
def home():
    return redirect(url_for('merge_pdf.serve_merge_html'))

@merge_pdf_bp.route('/mergepdf')
def serve_merge_html():
    return render_template('mergepdf.html')

@merge_pdf_bp.route('/start-merge', methods=['POST'])
def start_merge():
    if 'pdfs' not in request.files:
        return jsonify({"success": False, "message": "No files uploaded"}), 400

    files = request.files.getlist('pdfs')
    if len(files) < 2:
        return jsonify({"success": False, "message": "Upload at least 2 PDFs"}), 400
    if len(files) > MAX_FILES:
        return jsonify({"success": False, "message": f"Max {MAX_FILES} files allowed"}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    create_session(session_id)
    update_session(session_id, status="uploading", progress=0)

    merger = PdfMerger()
    saved_files = []
    total = len(files)

    try:
        for idx, file in enumerate(files, start=1):
            filename = secure_filename(file.filename)
            if not allowed_file(filename):
                raise ValueError("Not a PDF")

            file.stream.seek(0, os.SEEK_END)
            if file.stream.tell() > MAX_FILE_SIZE_BYTES:
                raise ValueError("File too large")
            file.stream.seek(0)

            path = os.path.join(session_folder, filename)
            file.save(path)
            saved_files.append(path)

            PdfReader(path)
            update_session(session_id, progress=int((idx / total) * 50))

            merger.append(path)

        update_session(session_id, status="merging", progress=70)

        merged_filename = f"{session_id}.pdf"
        merged_path = os.path.join(MERGED_FOLDER, merged_filename)

        merger.write(merged_path)
        merger.close()

        update_session(session_id, status="done", progress=100, merged_filename=merged_filename)

        return jsonify({"success": True, "session_id": session_id})

    except Exception as e:
        try:
            merger.close()
        except:
            pass
        return jsonify({"success": False, "message": str(e)}), 500

@merge_pdf_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"success": False, "message": "Missing session_id"}), 400

    session = local_sessions.get(session_id)
    if not session:
        return jsonify({"success": False, "message": "Session not found"}), 404

    # إذا الدمج لم ينتهي بعد → نعيد JSON لتحديث progress
    if session["status"] != "done":
        return jsonify({
            "success": True,
            "status": session["status"],
            "progress": session["progress"],
            "message": session["message"],
            "merged_filename": None
        })

    # إذا الدمج انتهى → إعادة صفحة HTML مع رابط التحميل
    merged_filename = session.get("merged_filename")
    if not merged_filename:
        return jsonify({"success": False, "message": "Merged file missing"}), 500

    download_link = url_for('merge_pdf.download_file', filename=merged_filename)
    return render_template("merge_result.html", filename=merged_filename, download_link=download_link)

@merge_pdf_bp.route('/download/<filename>')
def download_file(filename):
    if ".." in filename or "/" in filename:
        return "Invalid filename", 400
    path = os.path.join(MERGED_FOLDER, filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_from_directory(MERGED_FOLDER, filename, as_attachment=True)


@merge_pdf_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    path = os.path.join(MERGED_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"success": True, "message": "File deleted"})
    else:
        return jsonify({"success": False, "message": "File not found"}), 404
