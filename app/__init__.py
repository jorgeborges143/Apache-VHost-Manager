from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from app.config import config_by_name

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.vhosts.routes import vhosts_bp
    from app.apache.modules import modules_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(vhosts_bp, url_prefix='/vhosts')
    app.register_blueprint(modules_bp, url_prefix='/apache')

    from app.errors.handlers import errors_bp
    app.register_blueprint(errors_bp)

    with app.app_context():
        db.create_all()
        _create_default_admin()

    return app


def _create_default_admin():
    import os
    from app.models import User
    from werkzeug.security import generate_password_hash

    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')

    if not User.query.filter_by(username=admin_username).first():
        admin = User(
            username=admin_username,
            password_hash=generate_password_hash(admin_password),
            role='admin',
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()

