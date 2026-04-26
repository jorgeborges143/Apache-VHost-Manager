"""
pytest fixtures for the Apache VHost Manager test suite.
"""

import pytest
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SITES_AVAILABLE_DIR': '/tmp/apache2/sites-available',
        'SITES_ENABLED_DIR': '/tmp/apache2/sites-enabled',
        'BACKUP_DIR': '/tmp/apache2/backups',
        'AUDIT_LOG_DIR': '/tmp/apache2/logs',
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def admin_user(app):
    """Create an admin user for authentication tests."""
    with app.app_context():
        user = User(
            username='testadmin',
            password_hash=generate_password_hash('testpassword'),
            role='admin',
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def auth_client(client, admin_user):
    """A test client that is already logged in as admin."""
    client.post('/auth/login', data={
        'username': 'testadmin',
        'password': 'testpassword'
    }, follow_redirects=True)
    return client

