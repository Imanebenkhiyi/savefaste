from flask import Blueprint, render_template, request, redirect, url_for, session, flash

auth_bp = Blueprint('auth', __name__, template_folder='templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # تحقق مؤقت (يمكن تغييره لاستخدام Firebase)
        if email == "test@example.com" and password == "123456":
            session['user'] = email
            flash('Logged in successfully!', 'success')
            return redirect(url_for('auth_login.dashboard'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth_login.login'))

    return render_template('login.html')


@auth_bp.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('auth_login.login'))
    return render_template('dashboard.html', user=session['user'])


@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth_login.login'))
