from flask import Flask

app = Flask(__name__)

from pdf_to_text import routes
