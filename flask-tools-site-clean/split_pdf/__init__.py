from flask import Blueprint

split_pdf_bp = Blueprint('split_pdf', __name__, template_folder='templates', static_folder='static', url_prefix='/splitpdf')

from . import routes
