import os
import uuid
from flask import Blueprint, request, jsonify, render_template, send_from_directory, redirect, url_for
from PyPDF2 import PdfReader, PdfWriter
from werkzeug.utils import secure_filename
from datetime import datetime

reorder_pages_bp= Blueprint(
    'reorder_pages', 
    __name__, 
    static_folder='static',    
    static_url_path='/reorder_pages/static',
    template_folder='templates'   # ← هذا هو المطلوب
)
UPLOAD_FOLDER = 'uploads'
REORDERED_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'reordered')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REORDERED_FOLDER, exist_ok=True)

@reorder_pages_bp.route('/')
def home():
    return redirect(url_for('reorder_pages.serve_reorder_html'))

@reorder_pages_bp.route('', methods=['GET'])
def serve_reorder_html():
    return render_template('reorderpages.html')

@reorder_pages_bp.route('/start-reorder', methods=['POST'])
def start_reorder():
    try:
        file = request.files.get('pdf')
        order = request.form.get('order')

        if not file or not order:
            return jsonify({"success": False, "message": "Missing file or order"}), 400

        filename = secure_filename(file.filename)
        session_id = str(uuid.uuid4())
        input_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
        file.save(input_path)

        reader = PdfReader(input_path)
        writer = PdfWriter()

        try:
            pages_order = [int(i.strip()) - 1 for i in order.split(',')]
        except ValueError:
            return jsonify({"success": False, "message": "Invalid page numbers format."}), 400

        for i in pages_order:
            if i < 0 or i >= len(reader.pages):
                return jsonify({"success": False, "message": f"Page number {i+1} is out of range."}), 400
            writer.add_page(reader.pages[i])

        output_filename = f"{session_id}_reordered.pdf"
        output_path = os.path.join(REORDERED_FOLDER, output_filename)

        with open(output_path, 'wb') as f:
            writer.write(f)

        return jsonify({"success": True, "session_id": session_id, "filename": output_filename})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@reorder_pages_bp.route('/done')
def done():
    session_id = request.args.get('session_id')
    filename = request.args.get('filename')

    if not session_id or not filename:
        return "Missing session_id or file", 400

    download_link = url_for('reorder_pages.download_file', filename=filename)

    return render_template('dowlandreorder.html', download_link=download_link)


@reorder_pages_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(REORDERED_FOLDER, filename)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_from_directory(REORDERED_FOLDER, filename, as_attachment=True)
   

@reorder_pages_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    path = os.path.join(REORDERED_FOLDER , filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"success": True, "message": "File deleted"})
    else:
        return jsonify({"success": False, "message": "File not found"}), 404
