import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from werkzeug.utils import secure_filename
from datetime import datetime

add_page_bp = Blueprint('add_page', __name__, template_folder='templates', static_folder='static')

UPLOAD_FOLDER = 'uploads'
ADDED_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'added')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ADDED_FOLDER, exist_ok=True)

# الصفحة الرئيسية
@add_page_bp.route('/')
def home():
    return redirect(url_for('add_page.serve_add_html'))

# عرض صفحة HTML
@add_page_bp.route('', methods=['GET'])
def serve_add_html():
    return render_template('addpage.html')

# تنفيذ عملية الإضافة
@add_page_bp.route('/start-add', methods=['POST'])
def start_add():
    if 'main_pdf' not in request.files or 'insert_pdf' not in request.files:
        return jsonify({"success": False, "message": "Missing files"}), 400

    main_file = request.files['main_pdf']
    insert_file = request.files['insert_pdf']
    insert_at = request.form.get('insert_at', '')
    insert_pages_str = request.form.get('insert_pages', '')  # استقبل قائمة الصفحات

    try:
        insert_at = int(insert_at)
    except ValueError:
        return jsonify({"success": False, "message": "Invalid insert_at page number"}), 400

    if not insert_pages_str.strip():
        return jsonify({"success": False, "message": "No insert pages specified"}), 400

    # دالة لتحليل نص الصفحات (مثال: "1,3,5-7" => [1,3,5,6,7])
    def parse_pages(pages_str):
        pages = set()
        parts = pages_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                start_end = part.split('-')
                if len(start_end) != 2:
                    raise ValueError(f"Invalid page range: {part}")
                start, end = start_end
                start, end = int(start), int(end)
                if start > end or start < 1:
                    raise ValueError(f"Invalid page range: {part}")
                pages.update(range(start, end+1))
            else:
                page = int(part)
                if page < 1:
                    raise ValueError(f"Invalid page number: {page}")
                pages.add(page)
        return sorted(pages)

    try:
        insert_pages = parse_pages(insert_pages_str)
    except Exception as e:
        return jsonify({"success": False, "message": f"Invalid insert_pages: {str(e)}"}), 400

    session_id = str(uuid.uuid4())
    main_path = os.path.join(UPLOAD_FOLDER, secure_filename(f"{session_id}_main.pdf"))
    insert_path = os.path.join(UPLOAD_FOLDER, secure_filename(f"{session_id}_insert.pdf"))
    output_filename = f"{session_id}_added.pdf"
    output_path = os.path.join(ADDED_FOLDER, output_filename)

    main_file.save(main_path)
    insert_file.save(insert_path)

    try:
        main_reader = PdfReader(main_path)
        insert_reader = PdfReader(insert_path)
        writer = PdfWriter()

        total_pages_main = len(main_reader.pages)
        total_pages_insert = len(insert_reader.pages)

        if insert_at < 0 or insert_at > total_pages_main:
            return jsonify({"success": False, "message": "Insert position page number out of range"}), 400

        # تحقق أن كل صفحة في insert_pages ضمن المدى الصحيح
        for p in insert_pages:
            if p < 1 or p > total_pages_insert:
                return jsonify({"success": False, "message": f"Insert page number {p} out of range"}), 400

        # أضف صفحات الملف الرئيسي حتى نقطة الإدراج
        for i in range(insert_at):
            writer.add_page(main_reader.pages[i])

        # أضف صفحات الإدخال المحددة (حسب القائمة insert_pages)
        for p in insert_pages:
            writer.add_page(insert_reader.pages[p - 1])

        # أضف بقية صفحات الملف الرئيسي بعد الإدراج
        for i in range(insert_at, total_pages_main):
            writer.add_page(main_reader.pages[i])

        with open(output_path, 'wb') as f:
            writer.write(f)

        return jsonify({"success": True, "file": output_filename})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# صفحة النجاح
@add_page_bp.route('/progress')
def progress():
    filename = request.args.get('file')
    if not filename:
        return "Missing filename", 400

    output_path = os.path.join(ADDED_FOLDER, filename)
    if not os.path.exists(output_path):
        return f"File not found: {filename}", 404

    download_link = url_for('add_page.download_added_file', filename=filename)
    return render_template('addpagedowland.html', download_link=download_link)


# تنزيل الملف النهائي
@add_page_bp.route('/download/<filename>')
def download_added_file(filename):
    file_path = os.path.join(ADDED_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_from_directory(ADDED_FOLDER, filename, as_attachment=True)

@add_page_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    path = os.path.join(ADDED_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"success": True, "message": "File deleted"})
    else:
        return jsonify({"success": False, "message": "File not found"}), 404
