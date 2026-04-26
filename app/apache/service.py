"""
Apache Service Layer

Safe subprocess wrappers for Apache2 management commands.
NEVER uses shell=True.
"""

import subprocess
from pathlib import Path


def _run_command(cmd_list):
    """
    Run a command safely without shell=True.
    Returns (returncode, stdout, stderr).
    """
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError as e:
        return -1, '', str(e)
    except Exception as e:
        return -1, '', str(e)


def apache_status():
    """Check if Apache is running."""
    returncode, stdout, stderr = _run_command(['systemctl', 'is-active', '--quiet', 'apache2'])
    return returncode == 0


def start_apache():
    """Start Apache."""
    returncode, stdout, stderr = _run_command(['sudo', 'systemctl', 'start', 'apache2'])
    return {'success': returncode == 0, 'output': stdout + stderr}


def stop_apache():
    """Stop Apache."""
    returncode, stdout, stderr = _run_command(['sudo', 'systemctl', 'stop', 'apache2'])
    return {'success': returncode == 0, 'output': stdout + stderr}


def restart_apache():
    """Restart Apache."""
    returncode, stdout, stderr = _run_command(['sudo', 'systemctl', 'restart', 'apache2'])
    return {'success': returncode == 0, 'output': stdout + stderr}


def reload_apache():
    """Reload Apache gracefully."""
    returncode, stdout, stderr = _run_command(['sudo', 'systemctl', 'reload', 'apache2'])
    return {'success': returncode == 0, 'output': stdout + stderr}


def configtest_result():
    """
    Run apache2ctl configtest.
    Returns dict with valid (bool) and message (str).
    """
    returncode, stdout, stderr = _run_command(['sudo', 'apache2ctl', 'configtest'])
    output = (stdout + stderr).strip()
    # apache2ctl returns 0 on "Syntax OK" even if there are warnings
    valid = 'Syntax OK' in output

    # Filter out harmless warning about FQDN so users only see real errors
    filtered_lines = [
        line for line in output.splitlines()
        if not line.startswith('AH00558:') and line.strip()
    ]
    clean_message = '\n'.join(filtered_lines) if filtered_lines else ('Syntax OK' if valid else output)

    return {'valid': valid, 'message': clean_message}


def run_a2ensite(filename):
    """Enable a site using a2ensite."""
    if not _is_safe_filename(filename):
        raise ValueError('Unsafe filename for a2ensite.')
    returncode, stdout, stderr = _run_command(['sudo', 'a2ensite', filename])
    return {'success': returncode == 0, 'output': stdout + stderr}


def run_a2dissite(filename):
    """Disable a site using a2dissite."""
    if not _is_safe_filename(filename):
        raise ValueError('Unsafe filename for a2dissite.')
    returncode, stdout, stderr = _run_command(['sudo', 'a2dissite', filename])
    return {'success': returncode == 0, 'output': stdout + stderr}


def _is_safe_filename(filename):
    """Ensure filename contains only safe characters."""
    name = Path(filename).name
    return all(c.isalnum() or c in '_-.' for c in name)

