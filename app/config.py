import os
from pathlib import Path

basedir = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{basedir / "apache_vhost_manager.db"}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BACKUP_DIR = Path(os.environ.get('BACKUP_DIR', basedir / 'backups' / 'data'))
    AUDIT_LOG_DIR = Path(os.environ.get('AUDIT_LOG_DIR', basedir / 'logs'))
    SITES_AVAILABLE_DIR = Path(os.environ.get('SITES_AVAILABLE_DIR', '/etc/apache2/sites-available'))
    SITES_ENABLED_DIR = Path(os.environ.get('SITES_ENABLED_DIR', '/etc/apache2/sites-enabled'))
    REQUIRED_MODULES = ['ssl', 'rewrite', 'headers', 'proxy', 'proxy_http', 'proxy_wstunnel']
    MAX_BACKUPS_PER_VHOST = int(os.environ.get('MAX_BACKUPS_PER_VHOST', '20'))
    WTF_CSRF_ENABLED = True


class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}

