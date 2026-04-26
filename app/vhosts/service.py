"""
Virtual Host Service Layer

Handles CRUD operations, filename sanitization, duplicate detection,
safe file I/O, and integration with backup/audit systems.
"""

import os
import re
from pathlib import Path
from flask import current_app
from app import db
from app.models import VirtualHost
from app.vhosts.generator import generate_config
from app.backups.manager import create_backup
from app.audit.logger import log_action

SAFE_FILENAME_RE = re.compile(r'^[a-zA-Z0-9_\-]+$')


def sanitize_filename(name):
    """Sanitize a string to be a safe Apache config filename."""
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '', name)
    if not sanitized:
        raise ValueError('Invalid filename: empty after sanitization.')
    return sanitized + '.conf'


def validate_no_path_traversal(path, base_dir):
    """Ensure a path does not escape the intended directory."""
    try:
        resolved = Path(path).resolve()
        base = Path(base_dir).resolve()
    except (OSError, RuntimeError):
        # .resolve() can fail on non-existent paths on some systems;
        # fall back to normalized absolute paths
        resolved = Path(os.path.abspath(path))
        base = Path(os.path.abspath(base_dir))
    if not resolved.is_relative_to(base):
        raise ValueError('Path traversal detected.')


def get_vhost_file_path(filename):
    """Return safe absolute path for a vhost config file."""
    if not SAFE_FILENAME_RE.match(Path(filename).stem):
        raise ValueError('Unsafe filename detected.')
    path = Path(current_app.config['SITES_AVAILABLE_DIR']) / filename
    validate_no_path_traversal(path, current_app.config['SITES_AVAILABLE_DIR'])
    return path


def get_enabled_link_path(filename):
    """Return safe absolute path for a sites-enabled symlink."""
    if not SAFE_FILENAME_RE.match(Path(filename).stem):
        raise ValueError('Unsafe filename detected.')
    path = Path(current_app.config['SITES_ENABLED_DIR']) / filename
    validate_no_path_traversal(path, current_app.config['SITES_ENABLED_DIR'])
    return path


def check_duplicate_server_name(server_name, exclude_id=None):
    """Check if another vhost already uses this ServerName."""
    query = VirtualHost.query.filter_by(server_name=server_name)
    if exclude_id:
        query = query.filter(VirtualHost.id != exclude_id)
    return query.first() is not None


def create_vhost(data, user=None):
    """Create a new virtual host in DB and filesystem."""
    filename = sanitize_filename(data.get('filename', data['server_name']))
    if check_duplicate_server_name(data['server_name']):
        raise ValueError(f'ServerName "{data["server_name"]}" is already in use.')

    vhost = VirtualHost(
        name=data.get('name', data['server_name']),
        filename=filename,
        vhost_type=data['vhost_type'],
        server_name=data['server_name'],
        server_alias=','.join(data.get('server_alias', [])),
        listen_port=data.get('listen_port', 80),
        document_root=data.get('document_root'),
        ssl_enabled=data.get('ssl_enabled', False),
        ssl_cert_file=data.get('ssl_cert_file'),
        ssl_key_file=data.get('ssl_key_file'),
        force_https=data.get('force_https', False),
        enabled=False,
        backend_protocol=data.get('backend_protocol', 'http'),
        backend_host=data.get('backend_host'),
        backend_port=data.get('backend_port'),
        backend_path=data.get('backend_path', '/'),
        proxy_path=data.get('proxy_path', '/'),
        preserve_host=data.get('preserve_host', False),
        websocket_support=data.get('websocket_support', False),
        proxy_timeout=data.get('proxy_timeout', 300),
        proxy_headers='\n'.join(data.get('proxy_headers', [])),
        response_headers='\n'.join(data.get('response_headers', [])),
        extra_security_headers=data.get('extra_security_headers', False),
        redirect_url=data.get('redirect_url'),
        redirect_permanent=data.get('redirect_permanent', True),
        error_log=data.get('error_log'),
        custom_log=data.get('custom_log'),
        directory_options=data.get('directory_options'),
        allow_override=data.get('allow_override'),
        require_directive=data.get('require_directive'),
        extra_directives=data.get('extra_directives'),
        created_by=user
    )

    vhost.config_content = generate_config(vhost)
    db.session.add(vhost)
    db.session.commit()

    # Write to filesystem
    file_path = get_vhost_file_path(filename)
    file_path.write_text(vhost.config_content, encoding='utf-8')

    log_action('create_vhost', target=vhost.server_name, result='success', user=user)
    return vhost


def update_vhost(vhost_id, data, user=None):
    """Update an existing virtual host with automatic backup."""
    vhost = VirtualHost.query.get_or_404(vhost_id)

    # Backup before edit
    create_backup(vhost, user=user)

    if data.get('server_name') and data['server_name'] != vhost.server_name:
        if check_duplicate_server_name(data['server_name'], exclude_id=vhost.id):
            raise ValueError(f'ServerName "{data["server_name"]}" is already in use.')
        vhost.server_name = data['server_name']

    vhost.name = data.get('name', vhost.name)
    vhost.server_alias = ','.join(data.get('server_alias', []))
    vhost.listen_port = data.get('listen_port', vhost.listen_port)
    vhost.document_root = data.get('document_root', vhost.document_root)
    vhost.ssl_enabled = data.get('ssl_enabled', vhost.ssl_enabled)
    vhost.ssl_cert_file = data.get('ssl_cert_file', vhost.ssl_cert_file)
    vhost.ssl_key_file = data.get('ssl_key_file', vhost.ssl_key_file)
    vhost.force_https = data.get('force_https', vhost.force_https)
    vhost.backend_protocol = data.get('backend_protocol', vhost.backend_protocol)
    vhost.backend_host = data.get('backend_host', vhost.backend_host)
    vhost.backend_port = data.get('backend_port', vhost.backend_port)
    vhost.backend_path = data.get('backend_path', vhost.backend_path)
    vhost.proxy_path = data.get('proxy_path', vhost.proxy_path)
    vhost.preserve_host = data.get('preserve_host', vhost.preserve_host)
    vhost.websocket_support = data.get('websocket_support', vhost.websocket_support)
    vhost.proxy_timeout = data.get('proxy_timeout', vhost.proxy_timeout)
    vhost.proxy_headers = '\n'.join(data.get('proxy_headers', []))
    vhost.response_headers = '\n'.join(data.get('response_headers', []))
    vhost.extra_security_headers = data.get('extra_security_headers', vhost.extra_security_headers)
    vhost.redirect_url = data.get('redirect_url', vhost.redirect_url)
    vhost.redirect_permanent = data.get('redirect_permanent', vhost.redirect_permanent)
    vhost.error_log = data.get('error_log', vhost.error_log)
    vhost.custom_log = data.get('custom_log', vhost.custom_log)
    vhost.directory_options = data.get('directory_options', vhost.directory_options)
    vhost.allow_override = data.get('allow_override', vhost.allow_override)
    vhost.require_directive = data.get('require_directive', vhost.require_directive)
    vhost.extra_directives = data.get('extra_directives', vhost.extra_directives)

    vhost.config_content = generate_config(vhost)
    db.session.commit()

    # Write updated config
    file_path = get_vhost_file_path(vhost.filename)
    file_path.write_text(vhost.config_content, encoding='utf-8')

    log_action('update_vhost', target=vhost.server_name, result='success', user=user)
    return vhost


def delete_vhost(vhost_id, user=None):
    """Delete a virtual host with automatic backup."""
    vhost = VirtualHost.query.get_or_404(vhost_id)

    # Backup before delete
    create_backup(vhost, user=user)

    # Disable first if enabled
    if vhost.enabled:
        from app.apache.service import run_a2dissite
        run_a2dissite(vhost.filename)
        vhost.enabled = False

    # Remove files
    file_path = get_vhost_file_path(vhost.filename)
    if file_path.exists():
        file_path.unlink()

    enabled_path = get_enabled_link_path(vhost.filename)
    if enabled_path.exists() or enabled_path.is_symlink():
        enabled_path.unlink()

    db.session.delete(vhost)
    db.session.commit()

    log_action('delete_vhost', target=vhost.server_name, result='success', user=user)


def enable_vhost(vhost_id, user=None):
    """Enable a virtual host using a2ensite."""
    from app.apache.service import run_a2ensite, reload_apache
    vhost = VirtualHost.query.get_or_404(vhost_id)
    run_a2ensite(vhost.filename)
    vhost.enabled = True
    db.session.commit()
    reload_apache()
    log_action('enable_vhost', target=vhost.server_name, result='success', user=user)


def disable_vhost(vhost_id, user=None):
    """Disable a virtual host using a2dissite."""
    from app.apache.service import run_a2dissite, reload_apache
    vhost = VirtualHost.query.get_or_404(vhost_id)
    run_a2dissite(vhost.filename)
    vhost.enabled = False
    db.session.commit()
    reload_apache()
    log_action('disable_vhost', target=vhost.server_name, result='success', user=user)

