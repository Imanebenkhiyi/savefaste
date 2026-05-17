from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from PyPDF2 import PdfReader, PdfWriter
import io, os
from werkzeug.utils import secure_filename

remove_password_bp = Blueprint('remove_password', __name__, template_folder='templates')

UPLOAD_FOLDER = 'static/unlocked'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@remove_password_bp.route('/')
def home():
    return redirect(url_for('remove_password.serve_remove_password_html'))

@remove_password_bp.route('', methods=['GET'])
def serve_remove_password_html():
    return render_template('removepassword.html')

@remove_password_bp.route('/process', methods=['POST'])
def process_pdf():
    pdf_file = request.files.get('pdf_file')
    password = request.form.get('password')

    if not pdf_file or not password:
        flash('Please upload a PDF file and enter the password.', 'error')
        return redirect(url_for('remove_password.serve_remove_password_html'))

    try:
        reader = PdfReader(pdf_file)
        if reader.is_encrypted:
            reader.decrypt(password)

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        # حفظ نسخة مؤقتة بدون كلمة سر
        filename = secure_filename(pdf_file.filename)
        output_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(output_path, 'wb') as f_out:
            writer.write(f_out)

        # إعادة التوجيه لعرض الصفحة الجديدة
        return redirect(url_for('remove_password.display_pdf', filename=filename))

    except Exception as e:
        flash(f'Failed to remove password: {str(e)}', 'error')
        return redirect(url_for('remove_password.serve_remove_password_html'))

@remove_password_bp.route('/view/<filename>')
def display_pdf(filename):
    return render_template('view_pdf.html', filename=filename)

@remove_password_bp.route('/download/<filename>')
def download_pdf(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)
