import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from werkzeug.utils import secure_filename
from datetime import datetime

add_password_pdf_bp = Blueprint(
    'add_password_pdf',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/add_password_static'
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads_password')
ENCRYPTED_FOLDER = os.path.join(BASE_DIR, 'encrypted')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENCRYPTED_FOLDER, exist_ok=True)


# -----------------------------
# الصفحة الرئيسية للأداة
# -----------------------------
@add_password_pdf_bp.route('/')
def serve_password_html():
    return render_template('addpassword.html')


# -----------------------------
# بدء عملية التشفير
# -----------------------------
@add_password_pdf_bp.route('/start-encrypt', methods=['POST'])
def start_encrypt():
    if 'pdf_file' not in request.files:
        return jsonify({"success": False, "message": "No PDF file uploaded"}), 400

    file = request.files['pdf_file']
    password = request.form.get('password', '').strip()

    # التحقق من المدخلات
    if not file or file.filename == '':
        return jsonify({"success": False, "message": "No PDF file selected"}), 400

    if not password:
        return jsonify({"success": False, "message": "Password is required"}), 400

    # لا تعتمد على file.content_type لأن بعض المتصفحات ترسله غلط
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "message": "Invalid file type. Upload a PDF."}), 400

    # إنشاء مجلد الجلسة
    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    filename = secure_filename(file.filename)
    original_path = os.path.join(session_folder, filename)
    file.save(original_path)

    # تأكد أن الملف ليس فارغاً — هذا هو سبب EOF marker not found
    if os.path.getsize(original_path) < 100:
        return jsonify({
            "success": False,
            "message": "Uploaded PDF is corrupted or incomplete (size too small)"
        }), 400

    try:
        reader = PdfReader(original_path)

        # تأكد أن الملف قابل للقراءة
        if len(reader.pages) == 0:
            return jsonify({
                "success": False,
                "message": "Invalid or empty PDF file."
            }), 400

        writer = PdfWriter()

        # نقل الصفحات
        for page in reader.pages:
            writer.add_page(page)

        # التشفير
        writer.encrypt(password)

        encrypted_filename = f"{session_id}.pdf"
        encrypted_path = os.path.join(ENCRYPTED_FOLDER, encrypted_filename)

        with open(encrypted_path, 'wb') as f_out:
            writer.write(f_out)

        return jsonify({
            "success": True,
            "session_id": session_id
        })

    except Exception as e:
        return jsonify({"success": False, "message": f"Encryption error: {str(e)}"}), 500

# -----------------------------
# صفحة النتيجة Progress
# -----------------------------
@add_password_pdf_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')

    if not session_id:
        return "Missing session ID", 400

    filename = f"{session_id}.pdf"
    encrypted_path = os.path.join(ENCRYPTED_FOLDER, filename)

    # إذا الملف المتشفر غير موجود → لم يكتمل التشفير
    if not os.path.exists(encrypted_path):
        return "Encryption not completed yet.", 404

    # إنشاء رابط التحميل
    download_link = url_for('add_password_pdf.download_file', filename=filename)

    # عرض صفحة النجاح
    return render_template(
        'addpasswordsucces.html',
        download_link=download_link,
        filename=filename
    )


# -----------------------------
# تحميل الملف بعد التشفير
# -----------------------------
@add_password_pdf_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(ENCRYPTED_FOLDER, filename)

    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(ENCRYPTED_FOLDER, filename, as_attachment=True)

@add_password_pdf_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_encrypted_file(filename):
    path = os.path.join(ENCRYPTED_FOLDER, filename)

    if os.path.exists(path):
        os.remove(path)
        return jsonify({"success": True, "message": "Encrypted file deleted"})
    else:
        return jsonify({"success": False, "message": "File not found"}), 404
