"""
Virtual Host Routes

CRUD operations, enable/disable, config download, import, and backend testing.
"""

import requests
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, send_from_directory, current_app, jsonify
)
from flask_login import login_required, current_user
from app import db
from app.models import VirtualHost
from app.vhosts.forms import VirtualHostForm
from app.vhosts.service import (
    create_vhost, update_vhost, delete_vhost,
    enable_vhost, disable_vhost, get_vhost_file_path,
    sanitize_filename, check_duplicate_server_name
)
from app.vhosts.generator import generate_config
from app.vhosts.parser import parse_vhost_config
from app.apache.service import configtest_result, reload_apache
from app.backups.manager import list_backups, restore_backup
from app.audit.logger import log_action

vhosts_bp = Blueprint('vhosts', __name__, template_folder='../templates')


@vhosts_bp.route('/')
@login_required
def list_vhosts():
    """List all virtual hosts with optional search/filter."""
    query = VirtualHost.query

    search = request.args.get('q', '').strip()
    vhost_type = request.args.get('type', '').strip()
    status = request.args.get('status', '').strip()

    if search:
        query = query.filter(
            db.or_(
                VirtualHost.server_name.ilike(f'%{search}%'),
                VirtualHost.name.ilike(f'%{search}%')
            )
        )
    if vhost_type:
        query = query.filter_by(vhost_type=vhost_type)
    if status == 'enabled':
        query = query.filter_by(enabled=True)
    elif status == 'disabled':
        query = query.filter_by(enabled=False)

    vhosts = query.order_by(VirtualHost.server_name).all()
    return render_template('vhosts/list.html', vhosts=vhosts, q=search, type=vhost_type, status=status)


@vhosts_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_vhost():
    """Create a new virtual host."""
    form = VirtualHostForm()
    if form.validate_on_submit():
        try:
            data = _form_to_dict(form)
            vhost = create_vhost(data, user=current_user)
            flash(f'Virtual host "{vhost.server_name}" created successfully.', 'success')
            return redirect(url_for('vhosts.detail_vhost', vhost_id=vhost.id))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating virtual host: {e}', 'danger')

    return render_template('vhosts/form.html', form=form, title='New Virtual Host')


@vhosts_bp.route('/<int:vhost_id>')
@login_required
def detail_vhost(vhost_id):
    """View virtual host details."""
    vhost = VirtualHost.query.get_or_404(vhost_id)
    backups = list_backups(vhost_id)
    return render_template('vhosts/detail.html', vhost=vhost, backups=backups)


@vhosts_bp.route('/<int:vhost_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_vhost(vhost_id):
    """Edit an existing virtual host."""
    vhost = VirtualHost.query.get_or_404(vhost_id)

    if request.method == 'POST':
        form = VirtualHostForm()
    else:
        # GET: populate manually to avoid FieldList + obj string-iteration issues
        form = VirtualHostForm(
            vhost_type=vhost.vhost_type,
            server_name=vhost.server_name,
            listen_port=vhost.listen_port,
            ssl_enabled=vhost.ssl_enabled,
            ssl_cert_file=vhost.ssl_cert_file or '',
            ssl_key_file=vhost.ssl_key_file or '',
            force_https=vhost.force_https,
            document_root=vhost.document_root or '',
            directory_options=vhost.directory_options or '',
            allow_override=vhost.allow_override or '',
            require_directive=vhost.require_directive or '',
            backend_protocol=vhost.backend_protocol or 'http',
            backend_host=vhost.backend_host or '',
            backend_port=vhost.backend_port or 8080,
            backend_path=vhost.backend_path or '/',
            proxy_path=vhost.proxy_path or '/',
            preserve_host=vhost.preserve_host,
            websocket_support=vhost.websocket_support,
            proxy_timeout=vhost.proxy_timeout or 300,
            extra_security_headers=vhost.extra_security_headers,
            redirect_url=vhost.redirect_url or '',
            redirect_permanent=vhost.redirect_permanent,
            error_log=vhost.error_log or '',
            custom_log=vhost.custom_log or '',
            extra_directives=vhost.extra_directives or '',
        )

        # Aliases
        aliases = [a.strip() for a in vhost.server_alias.split(',') if a.strip()] if vhost.server_alias else []
        for alias in aliases[:10]:
            form.server_alias.append_entry(alias)

        # Proxy headers
        if vhost.proxy_headers:
            for line in vhost.proxy_headers.splitlines()[:10]:
                parts = line.strip().split(None, 1)
                if parts:
                    form.request_headers.append_entry({'key': parts[0], 'value': parts[1] if len(parts) > 1 else ''})

        # Response headers
        if vhost.response_headers:
            for line in vhost.response_headers.splitlines()[:10]:
                parts = line.strip().split(None, 1)
                if parts:
                    form.response_headers.append_entry({'key': parts[0], 'value': parts[1] if len(parts) > 1 else ''})

    if form.validate_on_submit():
        try:
            data = _form_to_dict(form)
            update_vhost(vhost_id, data, user=current_user)
            flash(f'Virtual host "{vhost.server_name}" updated successfully.', 'success')
            return redirect(url_for('vhosts.detail_vhost', vhost_id=vhost_id))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating virtual host: {e}', 'danger')

    return render_template('vhosts/form.html', form=form, vhost=vhost, title='Edit Virtual Host')


@vhosts_bp.route('/<int:vhost_id>/delete', methods=['POST'])
@login_required
def delete_vhost_route(vhost_id):
    """Delete a virtual host."""
    vhost = VirtualHost.query.get_or_404(vhost_id)
    try:
        server_name = vhost.server_name
        delete_vhost(vhost_id, user=current_user)
        flash(f'Virtual host "{server_name}" deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting virtual host: {e}', 'danger')
    return redirect(url_for('vhosts.list_vhosts'))


@vhosts_bp.route('/<int:vhost_id>/enable', methods=['POST'])
@login_required
def enable_vhost_route(vhost_id):
    """Enable a virtual host."""
    try:
        enable_vhost(vhost_id, user=current_user)
        flash('Virtual host enabled.', 'success')
    except Exception as e:
        flash(f'Error enabling virtual host: {e}', 'danger')
    return redirect(url_for('vhosts.list_vhosts'))


@vhosts_bp.route('/<int:vhost_id>/disable', methods=['POST'])
@login_required
def disable_vhost_route(vhost_id):
    """Disable a virtual host."""
    try:
        disable_vhost(vhost_id, user=current_user)
        flash('Virtual host disabled.', 'success')
    except Exception as e:
        flash(f'Error disabling virtual host: {e}', 'danger')
    return redirect(url_for('vhosts.list_vhosts'))


@vhosts_bp.route('/<int:vhost_id>/download')
@login_required
def download_config(vhost_id):
    """Download the generated Apache config file."""
    vhost = VirtualHost.query.get_or_404(vhost_id)
    from io import BytesIO
    from flask import send_file
    config_bytes = vhost.config_content.encode('utf-8')
    return send_file(
        BytesIO(config_bytes),
        mimetype='text/plain',
        as_attachment=True,
        download_name=vhost.filename
    )


@vhosts_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_vhost():
    """Import an existing Apache config file."""
    if request.method == 'POST':
        filename = request.form.get('filename', '').strip()
        raw_content = request.form.get('config_content', '').strip()

        if not filename or not raw_content:
            flash('Filename and config content are required.', 'danger')
            return render_template('vhosts/import.html')

        try:
            safe_filename = sanitize_filename(filename)
            parsed = parse_vhost_config(raw_content)

            # Detect type
            vhost_type = parsed.get('vhost_type', 'static')

            # Build data dict
            data = {
                'name': parsed.get('server_name', filename),
                'filename': safe_filename,
                'vhost_type': vhost_type,
                'server_name': parsed.get('server_name', 'example.com'),
                'server_alias': parsed.get('server_alias', []),
                'listen_port': 80,
                'document_root': parsed.get('document_root'),
                'ssl_enabled': parsed.get('ssl_enabled', False),
                'ssl_cert_file': parsed.get('ssl_cert_file'),
                'ssl_key_file': parsed.get('ssl_key_file'),
                'force_https': parsed.get('force_https', False),
                'error_log': parsed.get('error_log'),
                'custom_log': parsed.get('custom_log'),
                'extra_directives': '\n'.join(parsed.get('unsupported_directives', [])),
            }

            if check_duplicate_server_name(data['server_name']):
                flash(f'ServerName "{data["server_name"]}" already exists.', 'danger')
                return render_template('vhosts/import.html', filename=filename, config_content=raw_content)

            vhost = create_vhost(data, user=current_user)
            vhost.raw_config = raw_content
            db.session.commit()

            flash(f'Imported virtual host "{vhost.server_name}" successfully.', 'success')
            return redirect(url_for('vhosts.detail_vhost', vhost_id=vhost.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Import failed: {e}', 'danger')

    return render_template('vhosts/import.html')


@vhosts_bp.route('/<int:vhost_id>/test-backend', methods=['POST'])
@login_required
def test_backend(vhost_id):
    """Test reverse proxy backend connectivity."""
    vhost = VirtualHost.query.get_or_404(vhost_id)
    if vhost.vhost_type != 'proxy':
        return jsonify({'success': False, 'message': 'Not a reverse proxy vhost.'})

    try:
        protocol = vhost.backend_protocol or 'http'
        host = vhost.backend_host or '127.0.0.1'
        port = vhost.backend_port or 80
        path = vhost.backend_path or '/'
        url = f"{protocol}://{host}:{port}{path}"

        response = requests.get(url, timeout=10, verify=False)
        return jsonify({
            'success': True,
            'url': url,
            'status_code': response.status_code,
            'response_time_ms': getattr(response, 'elapsed', None) and response.elapsed.total_seconds() * 1000,
            'message': f'Backend responded with HTTP {response.status_code}'
        })
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'message': 'Backend connection timed out.'})
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'message': 'Could not connect to backend.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@vhosts_bp.route('/<int:vhost_id>/backups')
@login_required
def vhost_backups(vhost_id):
    """View backups for a virtual host."""
    vhost = VirtualHost.query.get_or_404(vhost_id)
    backups = list_backups(vhost_id)
    return render_template('vhosts/backups.html', vhost=vhost, backups=backups)


@vhosts_bp.route('/backups/<int:backup_id>/restore', methods=['POST'])
@login_required
def restore_backup_route(backup_id):
    """Restore a virtual host from a backup."""
    try:
        vhost = restore_backup(backup_id, user=current_user)
        flash(f'Virtual host "{vhost.server_name}" restored from backup.', 'success')
        return redirect(url_for('vhosts.detail_vhost', vhost_id=vhost.id))
    except Exception as e:
        flash(f'Restore failed: {e}', 'danger')
        return redirect(url_for('vhosts.list_vhosts'))


def _form_to_dict(form):
    """Convert a validated VirtualHostForm into a plain dict for the service layer."""
    data = {
        'vhost_type': form.vhost_type.data,
        'server_name': form.server_name.data,
        'server_alias': [a for a in form.server_alias.data if a],
        'listen_port': form.listen_port.data,
        'ssl_enabled': form.ssl_enabled.data,
        'ssl_cert_file': form.ssl_cert_file.data or None,
        'ssl_key_file': form.ssl_key_file.data or None,
        'force_https': form.force_https.data,
        'document_root': form.document_root.data or None,
        'directory_options': form.directory_options.data or None,
        'allow_override': form.allow_override.data or None,
        'require_directive': form.require_directive.data or None,
        'backend_protocol': form.backend_protocol.data,
        'backend_host': form.backend_host.data or None,
        'backend_port': form.backend_port.data,
        'backend_path': form.backend_path.data or '/',
        'proxy_path': form.proxy_path.data or '/',
        'preserve_host': form.preserve_host.data,
        'websocket_support': form.websocket_support.data,
        'proxy_timeout': form.proxy_timeout.data,
        'proxy_headers': [f"{h['key']} {h['value']}" for h in form.request_headers.data if h.get('key')],
        'response_headers': [f"{h['key']} {h['value']}" for h in form.response_headers.data if h.get('key')],
        'extra_security_headers': form.extra_security_headers.data,
        'redirect_url': form.redirect_url.data or None,
        'redirect_permanent': form.redirect_permanent.data,
        'error_log': form.error_log.data or None,
        'custom_log': form.custom_log.data or None,
        'extra_directives': form.extra_directives.data or None,
    }
    return data

