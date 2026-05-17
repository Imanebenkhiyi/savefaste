# blog/routes.py

from flask import Blueprint, render_template, redirect, url_for

blog_bp = Blueprint(
    'blogger',
    __name__,
    static_folder='static',
    static_url_path='/blogger/static',
    template_folder='templates'
)

# /blog/ → Redirect to /blog/articles
@blog_bp.route('/')
def home():
    return redirect(url_for('blogger.blog_home'))

# عرض قائمة مقالات المدونة
@blog_bp.route('/articles', methods=['GET'])
def blog_home():
    return render_template('blog.html')  # يحتوي على روابط للمقالات

# عرض مقال محدد (مثلاً: merge PDF article)
@blog_bp.route('/mergearticle', methods=['GET'])
def merge_article():
    return render_template('mergearticle.html')

@blog_bp.route('/splitarticle', methods=['GET'])
def split_article():
    return render_template('splitarticle.html')

@blog_bp.route('/pdfwordarticle', methods=['GET'])
def pdfwoord_article():
    return render_template('pdfwordarticle.html')

@blog_bp.route('/wordpffarticle', methods=['GET'])
def wordpdff_article():
    return render_template('wordpffarticle.html')





