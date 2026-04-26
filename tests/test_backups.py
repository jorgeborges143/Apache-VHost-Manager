"""
Unit tests for backup creation and restoration.
"""

import pytest
from pathlib import Path
from app import db
from app.models import VirtualHost, Backup
from app.backups.manager import create_backup, list_backups, restore_backup


@pytest.fixture
def sample_vhost(app):
    with app.app_context():
        vhost = VirtualHost(
            name='backup-test',
            filename='backup-test.conf',
            vhost_type='static',
            server_name='backup.example.com',
            listen_port=80,
            document_root='/var/www/backup',
            config_content='<VirtualHost *:80>\n    ServerName backup.example.com\n</VirtualHost>'
        )
        db.session.add(vhost)
        db.session.commit()
        return vhost


def test_create_backup(app, sample_vhost):
    with app.app_context():
        backup = create_backup(sample_vhost)
        assert backup.id is not None
        assert backup.vhost_id == sample_vhost.id
        assert backup.filename.startswith('backup-test_')
        assert backup.filename.endswith('.conf')
        assert Path(backup.backup_path).exists()

        content = Path(backup.backup_path).read_text()
        assert 'ServerName backup.example.com' in content


def test_list_backups(app, sample_vhost):
    with app.app_context():
        create_backup(sample_vhost)
        create_backup(sample_vhost)
        backups = list_backups(sample_vhost.id)
        assert len(backups) == 2


def test_restore_backup(app, sample_vhost):
    with app.app_context():
        # Create initial backup
        backup = create_backup(sample_vhost)

        # Modify vhost config
        sample_vhost.config_content = 'MODIFIED CONFIG'
        db.session.commit()

        # Restore
        restored = restore_backup(backup.id)
        assert restored.config_content == '<VirtualHost *:80>\n    ServerName backup.example.com\n</VirtualHost>'


def test_backup_cleanup_old(app, sample_vhost):
    with app.app_context():
        app.config['MAX_BACKUPS_PER_VHOST'] = 2
        for _ in range(5):
            create_backup(sample_vhost)

        backups = list_backups(sample_vhost.id)
        assert len(backups) == 2

