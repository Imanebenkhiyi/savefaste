from flask import Blueprint, render_template, request, redirect, url_for

contact_bp = Blueprint('contact', __name__, template_folder='templates')

@contact_bp.route('/contact')
def contact():
    return render_template('contactus.html')

@contact_bp.route('/submit-contact', methods=['POST'])
def submit_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    message = request.form.get('message')

    # معالجة البيانات (إرسال بريد - حفظ في DB - الخ)
    print(f"Name: {name}, Email: {email}, Subject: {subject}, Message: {message}")

    return redirect(url_for('contact.contact'))
