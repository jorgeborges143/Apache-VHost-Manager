from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='admin', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'


class VirtualHost(db.Model):
    __tablename__ = 'virtual_hosts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), unique=True, nullable=False, index=True)
    vhost_type = db.Column(db.String(20), nullable=False)  # static, proxy, redirect
    server_name = db.Column(db.String(255), nullable=False, index=True)
    server_alias = db.Column(db.Text, default='')
    listen_port = db.Column(db.Integer, default=80, nullable=False)
    document_root = db.Column(db.String(500), nullable=True)
    ssl_enabled = db.Column(db.Boolean, default=False, nullable=False)
    ssl_cert_file = db.Column(db.String(500), nullable=True)
    ssl_key_file = db.Column(db.String(500), nullable=True)
    force_https = db.Column(db.Boolean, default=False, nullable=False)
    enabled = db.Column(db.Boolean, default=False, nullable=False)
    config_content = db.Column(db.Text, nullable=False)
    raw_config = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User', backref='vhosts')

    # Proxy-specific fields (stored as JSON-like text for flexibility)
    backend_protocol = db.Column(db.String(10), default='http')
    backend_host = db.Column(db.String(255), nullable=True)
    backend_port = db.Column(db.Integer, nullable=True)
    backend_path = db.Column(db.String(255), default='/')
    proxy_path = db.Column(db.String(255), default='/')
    preserve_host = db.Column(db.Boolean, default=False)
    websocket_support = db.Column(db.Boolean, default=False)
    proxy_timeout = db.Column(db.Integer, default=300)
    proxy_headers = db.Column(db.Text, default='')
    response_headers = db.Column(db.Text, default='')
    extra_security_headers = db.Column(db.Boolean, default=False)

    # Redirect-specific fields
    redirect_url = db.Column(db.String(500), nullable=True)
    redirect_permanent = db.Column(db.Boolean, default=True)

    # Common fields
    error_log = db.Column(db.String(500), nullable=True)
    custom_log = db.Column(db.String(500), nullable=True)
    directory_options = db.Column(db.String(255), nullable=True)
    allow_override = db.Column(db.String(50), nullable=True)
    require_directive = db.Column(db.String(255), nullable=True)
    extra_directives = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<VirtualHost {self.server_name}>'


class Backup(db.Model):
    __tablename__ = 'backups'
    id = db.Column(db.Integer, primary_key=True)
    vhost_id = db.Column(db.Integer, db.ForeignKey('virtual_hosts.id'), nullable=False)
    vhost = db.relationship('VirtualHost', backref='backups')
    filename = db.Column(db.String(255), nullable=False)
    backup_path = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User')

    def __repr__(self):
        return f'<Backup {self.filename}>'


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    username = db.Column(db.String(80), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    target = db.Column(db.String(255), nullable=True)
    result = db.Column(db.String(20), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)

    def __repr__(self):
        return f'<AuditLog {self.action} {self.target}>'

