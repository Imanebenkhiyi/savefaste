from flask import Blueprint


compress_pdf_bp = Blueprint(
    'compress_pdf',
    __name__,
    static_folder='static',
    static_url_path='/compress_pdf/static',
    template_folder='templates'
)

from .routes import compress_pdf_bp
