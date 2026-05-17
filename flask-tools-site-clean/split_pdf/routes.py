import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from werkzeug.utils import secure_filename
from datetime import datetime
import zipfile

from flask import Blueprint

split_pdf_bp = Blueprint(
    'split_pdf', 
    __name__, 
    static_folder='static',    
    static_url_path='/split_pdf/static',
    template_folder='templates'   # ← هذا هو المطلوب
)


UPLOAD_FOLDER = 'uploads'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SPLIT_FOLDER = os.path.join(BASE_DIR, 'split_files')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SPLIT_FOLDER, exist_ok=True)

def parse_page_ranges(pages_str, max_page):
    """
    تحويل نص مثل "1-3,5,7-8" إلى قائمة أرقام صفحات (0-indexed)
    """
    pages = set()
    parts = pages_str.split(',')
    for part in parts:
        if '-' in part:
            start, end = part.split('-')
            start, end = int(start), int(end)
            pages.update(range(start-1, min(end, max_page)))
        else:
            p = int(part)
            if 1 <= p <= max_page:
                pages.add(p-1)
    return sorted(pages)

@split_pdf_bp.route('/')
def home():
    return redirect(url_for('split_pdf.serve_split_html'))

@split_pdf_bp.route('', methods=['GET'])
def serve_split_html():
    return render_template('splitpdf.html')

@split_pdf_bp.route('/start-split', methods=['POST'])
def start_split():
    if 'pdf' not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files['pdf']
    filename = secure_filename(file.filename)
    if not filename.lower().endswith('.pdf'):
        return jsonify({"success": False, "message": "Uploaded file is not a PDF"}), 400

    pages_str = request.form.get('pages')  # مثال: "1-3,5"
    split_each = request.form.get('split_each') == 'on'  # checkbox
    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    pdf_path = os.path.join(session_folder, filename)
    file.save(pdf_path)

    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        output_files = []

        if split_each:
            # كل صفحة ملف منفصل
            for i in range(total_pages):
                writer = PdfWriter()
                writer.add_page(reader.pages[i])
                out_filename = f"{session_id}_page_{i+1}.pdf"
                out_path = os.path.join(SPLIT_FOLDER, out_filename)
                with open(out_path, 'wb') as f_out:
                    writer.write(f_out)
                output_files.append(out_filename)

        elif pages_str:
            pages = parse_page_ranges(pages_str, total_pages)
            writer = PdfWriter()
            for p in pages:
                writer.add_page(reader.pages[p])
            out_filename = f"{session_id}_split.pdf"
            out_path = os.path.join(SPLIT_FOLDER, out_filename)
            with open(out_path, 'wb') as f_out:
                writer.write(f_out)
            output_files.append(out_filename)

        else:
            return jsonify({"success": False, "message": "No split option selected"}), 400

        # لو أكثر من ملف نضغطهم
        if len(output_files) > 1:
            zip_name = f"{session_id}_split.zip"
            zip_path = os.path.join(SPLIT_FOLDER, zip_name)
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_name in output_files:
                    zipf.write(os.path.join(SPLIT_FOLDER, file_name), file_name)
            return jsonify({"success": True, "session_id": session_id, "zip_file": zip_name})

        return jsonify({"success": True, "session_id": session_id, "file": output_files[0]})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@split_pdf_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Missing session ID", 400

    # تحقق لو ملف ZIP موجود أو ملف PDF مفرد
    for f in os.listdir(SPLIT_FOLDER):
        if f.startswith(session_id):
            file_path = os.path.join(SPLIT_FOLDER, f)
            download_link = url_for('split_pdf.download_file', filename=f)
            return render_template('split_success.html', download_link=download_link)

    return "Split not completed yet or session not found.", 404

@split_pdf_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(SPLIT_FOLDER, filename)
    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(SPLIT_FOLDER, filename, as_attachment=True)

