from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.auth.forms import LoginForm
from app.models import User
from app.audit.logger import log_action

auth_bp = Blueprint('auth', __name__, template_folder='../templates')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.is_active:
                flash('Your account is disabled.', 'danger')
                log_action('login', target=user.username, result='failure', details='Account disabled')
                return render_template('login.html', form=form)

            login_user(user)
            user.last_login = datetime.utcnow()
            from app import db
            db.session.commit()

            log_action('login', target=user.username, result='success')
            next_page = request.args.get('next')
            flash(f'Welcome, {user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            log_action('login', target=form.username.data, result='failure', details='Invalid credentials')
            flash('Invalid username or password.', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    log_action('logout', target=current_user.username, result='success')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

