"""
Audit Logger

Logs all admin actions to the database and optionally to a text file.
"""

import logging
from pathlib import Path
from flask import current_app, request
from app import db
from app.models import AuditLog


def _ensure_audit_log_dir():
    log_dir = Path(current_app.config.get('AUDIT_LOG_DIR', 'logs'))
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _get_file_logger():
    log_dir = _ensure_audit_log_dir()
    log_file = log_dir / 'audit.log'
    logger = logging.getLogger('audit_file')
    if not logger.handlers:
        handler = logging.FileHandler(log_file, encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(message)s'
        ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def log_action(action, target=None, result='success', details=None, user=None):
    """
    Log an admin action to the database and optionally to a file.

    Args:
        action: Action name (e.g., 'login', 'create_vhost')
        target: Target of the action (e.g., vhost server_name)
        result: 'success' or 'failure'
        details: Optional extra details
        user: User object or None
    """
    username = user.username if user else (getattr(request, 'remote_user', None) or 'system')
    ip_address = request.remote_addr if request else None

    # Database log
    audit_entry = AuditLog(
        username=username,
        action=action,
        target=target,
        result=result,
        details=details,
        ip_address=ip_address
    )
    db.session.add(audit_entry)
    db.session.commit()

    # File log
    try:
        file_logger = _get_file_logger()
        file_logger.info(
            f"user={username} action={action} target={target} result={result} ip={ip_address} details={details}"
        )
    except Exception:
        pass

