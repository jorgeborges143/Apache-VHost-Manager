"""
Apache Module Management

Detects required module status and enables missing modules safely.
"""

import re
from flask import Blueprint, jsonify, flash, redirect, url_for
from flask_login import login_required
from app.config import Config
from app.apache.service import _run_command, reload_apache, configtest_result
from app.audit.logger import log_action

modules_bp = Blueprint('modules', __name__, template_folder='../templates')


def get_module_status():
    """
    Check the status of all required Apache modules.
    Returns a list of dicts: {name, enabled}.
    """
    returncode, stdout, stderr = _run_command(['apache2ctl', '-M'])
    if returncode != 0:
        # Fallback: try apachectl or just check /etc/apache2/mods-enabled/
        returncode, stdout, stderr = _run_command(['apachectl', '-M'])

    loaded_modules = []
    if stdout:
        for line in stdout.splitlines():
            match = re.search(r'(\w+)_module', line)
            if match:
                loaded_modules.append(match.group(1))

    # Also check mods-enabled directory as fallback
    try:
        from pathlib import Path
        mods_enabled = Path('/etc/apache2/mods-enabled')
        if mods_enabled.exists():
            for f in mods_enabled.iterdir():
                if f.suffix == '.load':
                    mod_name = f.stem
                    if mod_name not in loaded_modules:
                        loaded_modules.append(mod_name)
    except Exception:
        pass

    results = []
    for mod in Config.REQUIRED_MODULES:
        results.append({
            'name': mod,
            'enabled': mod in loaded_modules
        })
    return results


def enable_module(module_name):
    """
    Enable an Apache module using a2enmod.
    Returns dict with success and message.
    """
    if not re.match(r'^[a-zA-Z0-9_]+$', module_name):
        return {'success': False, 'message': 'Invalid module name.'}

    returncode, stdout, stderr = _run_command(['sudo', 'a2enmod', module_name])
    output = (stdout + stderr).strip()

    if returncode == 0:
        # Run configtest after enabling
        test_result = configtest_result()
        if test_result['valid']:
            reload_apache()
            return {'success': True, 'message': f'Module {module_name} enabled. Config valid. Apache reloaded.', 'reloaded': True}
        else:
            # Disable module if config is invalid
            _run_command(['sudo', 'a2dismod', module_name])
            return {'success': False, 'message': f'Module {module_name} caused config error: {test_result["message"]}', 'reloaded': False}
    else:
        return {'success': False, 'message': output}


@modules_bp.route('/modules')
@login_required
def list_modules():
    """JSON endpoint for module status."""
    return jsonify(get_module_status())


@modules_bp.route('/modules/enable/<module_name>')
@login_required
def enable_module_route(module_name):
    """Enable a module via web UI."""
    result = enable_module(module_name)
    if result['success']:
        flash(result['message'], 'success')
        log_action('enable_module', target=module_name, result='success')
    else:
        flash(result['message'], 'danger')
        log_action('enable_module', target=module_name, result='failure', details=result['message'])
    return redirect(url_for('dashboard.index'))

