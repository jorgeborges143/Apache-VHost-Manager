"""
Unit tests for input validation and safe filename handling.
"""

import pytest
from app.vhosts.service import sanitize_filename, validate_no_path_traversal, check_duplicate_server_name
from app.vhosts.forms import VirtualHostForm


class TestSanitizeFilename:
    def test_sanitize_simple_name(self):
        assert sanitize_filename('example.com') == 'examplecom.conf'

    def test_sanitize_with_dots(self):
        assert sanitize_filename('sub.example.com') == 'subexamplecom.conf'

    def test_sanitize_with_hyphens(self):
        assert sanitize_filename('my-site') == 'my-site.conf'

    def test_sanitize_with_underscores(self):
        assert sanitize_filename('my_site') == 'my_site.conf'

    def test_sanitize_rejects_empty(self):
        with pytest.raises(ValueError, match='empty after sanitization'):
            sanitize_filename('!!!')

    def test_sanitize_blocks_path_traversal_attempts(self):
        with pytest.raises(ValueError):
            sanitize_filename('../../../etc/passwd')


class TestPathTraversal:
    def test_valid_path_within_base(self, app):
        with app.app_context():
            path = '/etc/apache2/sites-available/example.conf'
            # Should not raise
            validate_no_path_traversal(path)

    def test_path_traversal_detected(self, app):
        with app.app_context():
            path = '/etc/apache2/sites-available/../../etc/passwd'
            with pytest.raises(ValueError, match='Path traversal'):
                validate_no_path_traversal(path)


class TestDuplicateServerName:
    def test_no_duplicate(self, app):
        with app.app_context():
            assert check_duplicate_server_name('unique.example.com') is False

    def test_duplicate_detected(self, app):
        from app import db
        from app.models import VirtualHost
        with app.app_context():
            vhost = VirtualHost(
                name='test',
                filename='test.conf',
                vhost_type='static',
                server_name='duplicate.example.com',
                listen_port=80,
                config_content='test'
            )
            db.session.add(vhost)
            db.session.commit()
            assert check_duplicate_server_name('duplicate.example.com') is True


class TestFormValidation:
    def test_valid_domain(self, app):
        with app.app_context():
            form = VirtualHostForm(data={
                'vhost_type': 'static',
                'server_name': 'example.com',
                'listen_port': 80,
            })
            assert form.validate() is True

    def test_invalid_domain(self, app):
        with app.app_context():
            form = VirtualHostForm(data={
                'vhost_type': 'static',
                'server_name': 'not a domain!',
                'listen_port': 80,
            })
            assert form.validate() is False
            assert 'server_name' in form.errors

    def test_port_out_of_range(self, app):
        with app.app_context():
            form = VirtualHostForm(data={
                'vhost_type': 'static',
                'server_name': 'example.com',
                'listen_port': 99999,
            })
            assert form.validate() is False
            assert 'listen_port' in form.errors

    def test_blocked_directives(self, app):
        with app.app_context():
            form = VirtualHostForm(data={
                'vhost_type': 'static',
                'server_name': 'example.com',
                'listen_port': 80,
                'extra_directives': 'Exec /bin/bash'
            })
            # WTForms custom validators don't always prevent validate() from returning True
            # depending on implementation, but we test the validation method directly
            try:
                form.validate_extra_directives(form.extra_directives)
                assert False, "Should have raised ValidationError"
            except Exception as e:
                assert 'not allowed' in str(e)

