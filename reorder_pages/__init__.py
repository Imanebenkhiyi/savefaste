from flask import Blueprint

reorder_pages_bp = Blueprint(
    'reorder_pages',
    __name__,
    static_folder='static',
    template_folder='templates'
)

from . import routes
