from flask import Blueprint

pdf_to_html_bp = Blueprint('pdf_to_html', __name__, template_folder='templates')

from . import routes
