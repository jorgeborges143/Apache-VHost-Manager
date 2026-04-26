"""
Backup Manager

Handles automatic backup creation before edits/deletes,
backup history, restoration, and cleanup.
"""

import shutil
from datetime import datetime
from pathlib import Path
from flask import current_app
from app import db
from app.models import Backup, VirtualHost
from app.vhosts.generator import generate_config


def _get_backup_dir():
    backup_dir = Path(current_app.config.get('BACKUP_DIR', 'backups/data'))
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def _cleanup_old_backups(vhost_id):
    max_backups = current_app.config.get('MAX_BACKUPS_PER_VHOST', 20)
    backups = Backup.query.filter_by(vhost_id=vhost_id).order_by(Backup.created_at.desc()).all()
    if len(backups) > max_backups:
        for old in backups[max_backups:]:
            path = Path(old.backup_path)
            if path.exists():
                path.unlink()
            db.session.delete(old)
        db.session.commit()


def create_backup(vhost, user=None):
    """
    Create a timestamped backup of a virtual host's config file and DB state.
    """
    backup_dir = _get_backup_dir()
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"{Path(vhost.filename).stem}_{timestamp}.conf"
    backup_path = backup_dir / backup_filename

    # Write current generated config to backup file
    config_content = vhost.config_content or generate_config(vhost)
    backup_path.write_text(config_content, encoding='utf-8')

    # Record in database
    backup = Backup(
        vhost_id=vhost.id,
        filename=backup_filename,
        backup_path=str(backup_path),
        created_by=user
    )
    db.session.add(backup)
    db.session.commit()

    _cleanup_old_backups(vhost.id)
    return backup


def list_backups(vhost_id):
    """Return all backups for a virtual host, newest first."""
    return Backup.query.filter_by(vhost_id=vhost_id).order_by(Backup.created_at.desc()).all()


def restore_backup(backup_id, user=None):
    """
    Restore a virtual host from a backup.
    Returns the restored VirtualHost object.
    """
    from app.audit.logger import log_action
    from app.vhosts.service import get_vhost_file_path

    backup = Backup.query.get_or_404(backup_id)
    vhost = backup.vhost

    if not Path(backup.backup_path).exists():
        raise FileNotFoundError(f"Backup file not found: {backup.backup_path}")

    # Read backup content
    restored_content = Path(backup.backup_path).read_text(encoding='utf-8')

    # Update DB
    vhost.config_content = restored_content
    vhost.raw_config = restored_content
    db.session.commit()

    # Write to filesystem
    file_path = get_vhost_file_path(vhost.filename)
    file_path.write_text(restored_content, encoding='utf-8')

    log_action('restore_backup', target=vhost.server_name, result='success', user=user)
    return vhost

