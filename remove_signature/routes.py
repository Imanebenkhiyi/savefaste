from flask import Blueprint, render_template, request, send_file, redirect, url_for
import fitz  # PyMuPDF
import io

remove_signature_bp = Blueprint('remove_signature', __name__, template_folder='templates')

@remove_signature_bp.route('/')
def home():
    return redirect(url_for('remove_signature.serve_remove_signature_html'))

@remove_signature_bp.route('', methods=['GET'])
def serve_remove_signature_html():
    return render_template('removesignature.html')

@remove_signature_bp.route('/process', methods=['POST'])
def remove_signature():
    try:
        if 'pdf' not in request.files:
            return {"success": False, "message": "No PDF uploaded"}, 400

        pdf_file = request.files['pdf']
        pdf_bytes = pdf_file.read()

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")  # ← هذه الطريقة أكثر أمانًا

        for page in doc:
            images = page.get_images(full=True)
            for img in images:
                xref = img[0]
                print(f"Removing image xref: {xref}")  # ← ديباگ لمعرفة ما يتم مسحه
                page._wrap_contents()
                try:
                    doc._delete_object(xref)  # ← تغيير من page إلى doc (مهم)
                except Exception as e:
                    print(f"Failed to delete object {xref}: {e}")

        output = io.BytesIO()
        doc.save(output)
        doc.close()
        output.seek(0)

        return send_file(output, as_attachment=True, download_name="cleaned.pdf", mimetype="application/pdf")

    except Exception as e:
        print(f"Error in remove_signature: {e}")  # ← طباعة الخطأ الحقيقية
        return {"success": False, "message": str(e)}, 500
