import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, render_template, redirect, url_for
from werkzeug.utils import secure_filename
import pdfplumber
import pandas as pd

pdf_to_excel_bp = Blueprint('pdf_to_excel', __name__, template_folder='templates',static_folder='static',
    static_url_path='/pdf_to_excel/static')

UPLOAD_FOLDER = 'uploads'
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
EXCEL_FOLDER = os.path.join(BASE_DIR, 'excels')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXCEL_FOLDER, exist_ok=True)

def make_unique_columns(columns):
    seen = {}
    result = []
    for col in columns:
        if col not in seen:
            seen[col] = 0
            result.append(col)
        else:
            seen[col] += 1
            new_col = f"{col}_{seen[col]}"
            while new_col in seen:
                seen[col] += 1
                new_col = f"{col}_{seen[col]}"
            seen[new_col] = 0
            result.append(new_col)
    return result

@pdf_to_excel_bp.route('/')
def home():
    return redirect(url_for('pdf_to_excel.serve_convert_html'))

@pdf_to_excel_bp.route('', methods=['GET'])
def serve_convert_html():
    return render_template('pdftoexcel.html')

@pdf_to_excel_bp.route('/start-convert', methods=['POST'])
def start_convert():
    if 'pdf' not in request.files:
        return jsonify({"success": False, "message": "No files uploaded"}), 400

    files = request.files.getlist('pdf')
    if len(files) < 1:
        return jsonify({"success": False, "message": "Please upload at least one PDF file."}), 400

    session_id = str(uuid.uuid4())
    session_folder = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_folder, exist_ok=True)

    excel_files = []
    try:
        for file in files:
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(session_folder, filename)
            file.save(pdf_path)

            with pdfplumber.open(pdf_path) as pdf:
                all_tables = []
                for page in pdf.pages:
                    tables = page.extract_tables()
                    for table in tables:
                        if len(table) < 2:
                            continue
                        cols = table[0]
                        unique_cols = make_unique_columns(cols)
                        df = pd.DataFrame(table[1:], columns=unique_cols)
                        all_tables.append(df)

                if not all_tables:
                    return jsonify({"success": False, "message": f"No tables found in {filename}"}), 400

                merged_df = pd.concat(all_tables, ignore_index=True)
                excel_filename = f"{os.path.splitext(filename)[0]}_{session_id}.xlsx"
                excel_path = os.path.join(EXCEL_FOLDER, excel_filename)
                merged_df.to_excel(excel_path, index=False)
                excel_files.append(excel_filename)

        return jsonify({"success": True, "session_id": session_id, "files": excel_files})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@pdf_to_excel_bp.route('/progress')
def progress():
    session_id = request.args.get('session_id')
    if not session_id:
        return "Missing session ID", 400

    excel_files = [f for f in os.listdir(EXCEL_FOLDER) if f.endswith(f"_{session_id}.xlsx")]
    if not excel_files:
        return "Conversion not completed yet or no files found.", 404

    # استخدم أول ملف تطابق
    actual_filename = excel_files[0]
    download_link = url_for('pdf_to_excel.download_file', filename=actual_filename)

    return render_template('pdfexcelsucce.html', download_link=download_link, filename=actual_filename)


@pdf_to_excel_bp.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(EXCEL_FOLDER, filename)
    if not os.path.exists(file_path):
        return f"❌ File not found at {file_path}", 404

    return send_from_directory(EXCEL_FOLDER, filename, as_attachment=True)

@pdf_to_excel_bp.route('/delete/<filename>', methods=['DELETE'])
def delete_excel_file(filename):
    path = os.path.join(EXCEL_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        return jsonify({"success": True, "message": "File deleted"})
    else:
        return jsonify({"success": False, "message": "File not found"}), 404
