from flask import Flask, render_template
from merge_pdf.routes import merge_pdf_bp
from split_pdf.routes import split_pdf_bp
from compress_pdf.routes import compress_pdf_bp
from reorder_pages.routes import reorder_pages_bp 
from delet_page.routes import delet_page_bp
from add_page.routes import add_page_bp
from rotate_page.routes import rotate_page_bp
from pdf_to_word.routes import pdf_to_word_bp
from pdf_to_excel.routes import pdf_to_excel_bp
from pdf_to_text.routes import pdf_to_text_bp
from pdf_to_html.routes import pdf_to_html_bp
from image_to_pdf.routes import image_to_pdf_bp
from pdf_to_image.routes import pdf_to_image_bp
from add_password_pdf.routes import add_password_pdf_bp
from remove_password.routes import remove_password_bp
from remove_signature.routes import remove_signature_bp
from word_to_pdf.routes import word_to_pdf_bp
from excel_to_pdf.routes import excel_to_pdf_bp
from pdf_to_ppt.routes import pdf_to_ppt_bp
from convert_webp.routes import convert_webp_bp
from convert_heic.routes import convert_heic_bp
from resize.routes import resize_bp
from compress.routes import compress_bp
from blogger.routes import blog_bp
from contact_us.route import contact_bp
from flask import Flask, render_template
import os

def create_app():
    app = Flask(__name__)
    app.secret_key = 'supersecretkey'

    app.register_blueprint(merge_pdf_bp, url_prefix='/mergepdf')
    app.register_blueprint(split_pdf_bp, url_prefix='/splitpdf')
    app.register_blueprint(compress_pdf_bp, url_prefix='/compresspdf')
    app.register_blueprint(reorder_pages_bp, url_prefix='/reorderpages')
    app.register_blueprint(delet_page_bp, url_prefix='/deletpage')
    app.register_blueprint(add_page_bp, url_prefix='/addpage')
    app.register_blueprint(rotate_page_bp, url_prefix='/rotatepage')
    app.register_blueprint(pdf_to_word_bp, url_prefix='/pdftoword')
    app.register_blueprint(pdf_to_excel_bp, url_prefix='/pdftoexcel')
    app.register_blueprint(pdf_to_text_bp, url_prefix='/pdftotext')
    app.register_blueprint(pdf_to_html_bp, url_prefix='/pdftohtml')
    app.register_blueprint(image_to_pdf_bp, url_prefix='/imagetopdf')
    app.register_blueprint(pdf_to_image_bp, url_prefix='/pdftoimage')
    app.register_blueprint(add_password_pdf_bp, url_prefix='/addpassword')
    app.register_blueprint(remove_password_bp, url_prefix='/removepassword')
    app.register_blueprint(remove_signature_bp, url_prefix='/removesignature')
    app.register_blueprint(word_to_pdf_bp, url_prefix='/wordtopdf')
    app.register_blueprint(excel_to_pdf_bp, url_prefix='/exceltopdf')
    app.register_blueprint(pdf_to_ppt_bp, url_prefix='/pdftoppt')
    app.register_blueprint(convert_webp_bp, url_prefix='/convertwebp')
    app.register_blueprint(convert_heic_bp, url_prefix='/convertheic')
    app.register_blueprint(resize_bp, url_prefix='/resizeimage')
    app.register_blueprint(compress_bp, url_prefix='/compressimage')
    app.register_blueprint(contact_bp, url_prefix='/contactus')
    app.register_blueprint(blog_bp, url_prefix='/blog')
    


    





    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/contactus')
    def contact():
       return render_template('contactus.html')
 
    @app.route('/privacypolicy')
    def privac():
       return render_template('privacypolicy.html')
    
    @app.route('/terms')
    def termsof():
       return render_template('terms.html')
    
    @app.route('/aboutus')
    def about():
       return render_template('aboutus.html')
 

    print(app.url_map)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)


    # في نهاية الملف
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
