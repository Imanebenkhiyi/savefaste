from flask import Blueprint

rotate_page_bp = Blueprint('rotate_page', __name__, template_folder='templates')

from . import routes
