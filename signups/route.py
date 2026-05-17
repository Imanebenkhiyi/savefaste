from flask import Blueprint, render_template, request, redirect, url_for, flash

sign_bp = Blueprint('sign', __name__, template_folder='templates')

@sign_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        # حفظ البيانات في Firebase أو DB
        print(f"Sign Up -> Name: {name}, Email: {email}, Password: {password}")

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('auth_login.login'))  # لاحظ الرابط إلى صفحة Login

    return render_template('signup.html')
