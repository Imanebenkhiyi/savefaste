import os
from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF

pdf_to_text_bp = Blueprint('pdf_to_text', __name__, template_folder='templates',static_folder='static',
    static_url_path='/pdf_to_text/static')

# إعداد مجلد التحميل في config (افتراضي لو لم يكن موجود)
UPLOAD_FOLDER = 'uploads'

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@pdf_to_text_bp .route('/')
def index():
    return render_template('pdftotext.html')

@pdf_to_text_bp .route('/convert', methods=['POST'])
def convert_pdf():
    if 'pdf_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part in the request'})

    file = request.files['pdf_file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})

    if file and allowed_file(file.filename):
        # مجلد التحميل ممكن تحديده في config، أو افتراضياً مجلد uploads
        upload_folder = current_app.config.get('UPLOAD_FOLDER', UPLOAD_FOLDER)
        os.makedirs(upload_folder, exist_ok=True)

        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        try:
            # فتح ملف PDF
            doc = fitz.open(filepath)
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            doc.close()

            # حفظ النص في ملف نصي بنفس اسم PDF
            txt_filename = filename.rsplit('.', 1)[0] + ".txt"
            txt_path = os.path.join(upload_folder, txt_filename)
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(full_text)

            # يمكنك تعديل الرد حسب حاجتك، هنا نرجع النص فقط
            return jsonify({'success': True, 'text': full_text})

        except Exception as e:
            return jsonify({'success': False, 'message': f'Error processing PDF: {str(e)}'})

    else:
        return jsonify({'success': False, 'message': 'Invalid file type. Only PDF allowed.'})
