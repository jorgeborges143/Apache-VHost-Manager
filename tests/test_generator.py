"""
Unit tests for Apache virtual host configuration generation.
"""

import pytest
from app.models import VirtualHost
from app.vhosts.generator import (
    generate_static_vhost,
    generate_proxy_vhost,
    generate_redirect_vhost,
    generate_config
)


class MockVhost:
    """Simple mock object simulating a VirtualHost model instance."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_generate_static_vhost_basic():
    vhost = MockVhost(
        vhost_type='static',
        server_name='example.com',
        server_alias='www.example.com,alias.example.com',
        listen_port=80,
        document_root='/var/www/example.com',
        directory_options='Indexes FollowSymLinks',
        allow_override='All',
        require_directive='all granted',
        error_log='/var/log/apache2/example.com-error.log',
        custom_log='/var/log/apache2/example.com-access.log',
        ssl_enabled=False,
        ssl_cert_file=None,
        ssl_key_file=None,
        force_https=False,
        extra_directives=None
    )
    config = generate_static_vhost(vhost)
    assert '<VirtualHost *:80>' in config
    assert 'ServerName example.com' in config
    assert 'ServerAlias www.example.com alias.example.com' in config
    assert 'DocumentRoot /var/www/example.com' in config
    assert 'Options Indexes FollowSymLinks' in config
    assert 'AllowOverride All' in config
    assert 'Require all granted' in config
    assert 'ErrorLog /var/log/apache2/example.com-error.log' in config
    assert 'CustomLog /var/log/apache2/example.com-access.log combined' in config


def test_generate_static_vhost_ssl_and_force_https():
    vhost = MockVhost(
        vhost_type='static',
        server_name='secure.example.com',
        server_alias='',
        listen_port=443,
        document_root='/var/www/secure',
        directory_options=None,
        allow_override=None,
        require_directive=None,
        error_log=None,
        custom_log=None,
        ssl_enabled=True,
        ssl_cert_file='/etc/ssl/certs/secure.crt',
        ssl_key_file='/etc/ssl/private/secure.key',
        force_https=True,
        extra_directives=None
    )
    config = generate_static_vhost(vhost)
    assert 'SSLEngine on' in config
    assert 'SSLCertificateFile /etc/ssl/certs/secure.crt' in config
    assert 'SSLCertificateKeyFile /etc/ssl/private/secure.key' in config
    assert 'RewriteEngine On' in config
    assert 'RewriteCond %{HTTPS} off' in config


def test_generate_proxy_vhost_basic():
    vhost = MockVhost(
        vhost_type='proxy',
        server_name='api.example.com',
        server_alias='',
        listen_port=80,
        error_log=None,
        custom_log=None,
        ssl_enabled=False,
        ssl_cert_file=None,
        ssl_key_file=None,
        force_https=False,
        backend_protocol='http',
        backend_host='127.0.0.1',
        backend_port=4999,
        backend_path='/',
        proxy_path='/',
        preserve_host=True,
        websocket_support=False,
        proxy_timeout=300,
        proxy_headers='',
        response_headers='',
        extra_security_headers=False,
        extra_directives=None
    )
    config = generate_proxy_vhost(vhost)
    assert '<VirtualHost *:80>' in config
    assert 'ServerName api.example.com' in config
    assert 'ProxyPreserveHost On' in config
    assert 'ProxyPass / http://127.0.0.1:4999/' in config
    assert 'ProxyPassReverse / http://127.0.0.1:4999/' in config
    assert 'ProxyTimeout 300' in config


def test_generate_proxy_vhost_websocket():
    vhost = MockVhost(
        vhost_type='proxy',
        server_name='ws.example.com',
        server_alias='',
        listen_port=80,
        error_log=None,
        custom_log=None,
        ssl_enabled=False,
        ssl_cert_file=None,
        ssl_key_file=None,
        force_https=False,
        backend_protocol='http',
        backend_host='127.0.0.1',
        backend_port=5000,
        backend_path='/',
        proxy_path='/',
        preserve_host=False,
        websocket_support=True,
        proxy_timeout=60,
        proxy_headers='',
        response_headers='',
        extra_security_headers=False,
        extra_directives=None
    )
    config = generate_proxy_vhost(vhost)
    assert 'RewriteCond %{HTTP:Upgrade} websocket [NC]' in config
    assert 'RewriteCond %{HTTP:Connection} upgrade [NC]' in config


def test_generate_proxy_vhost_security_headers():
    vhost = MockVhost(
        vhost_type='proxy',
        server_name='app.example.com',
        server_alias='',
        listen_port=443,
        error_log=None,
        custom_log=None,
        ssl_enabled=True,
        ssl_cert_file=None,
        ssl_key_file=None,
        force_https=False,
        backend_protocol='https',
        backend_host='localhost',
        backend_port=8080,
        backend_path='/api',
        proxy_path='/api',
        preserve_host=False,
        websocket_support=False,
        proxy_timeout=300,
        proxy_headers='Set X-Real-IP %{REMOTE_ADDR}',
        response_headers='always set X-Custom-Header value',
        extra_security_headers=True,
        extra_directives=None
    )
    config = generate_proxy_vhost(vhost)
    assert 'X-Frame-Options' in config
    assert 'X-Content-Type-Options' in config
    assert 'Referrer-Policy' in config
    assert 'RequestHeader Set X-Real-IP %{REMOTE_ADDR}' in config
    assert 'Header always set X-Custom-Header value' in config


def test_generate_redirect_vhost_permanent():
    vhost = MockVhost(
        vhost_type='redirect',
        server_name='old.example.com',
        server_alias='',
        listen_port=80,
        error_log=None,
        custom_log=None,
        ssl_enabled=False,
        ssl_cert_file=None,
        ssl_key_file=None,
        force_https=False,
        redirect_url='https://new.example.com/',
        redirect_permanent=True,
        extra_directives=None
    )
    config = generate_redirect_vhost(vhost)
    assert 'Redirect permanent "/" "https://new.example.com/"' in config


def test_generate_redirect_vhost_temporary():
    vhost = MockVhost(
        vhost_type='redirect',
        server_name='temp.example.com',
        server_alias='',
        listen_port=80,
        error_log=None,
        custom_log=None,
        ssl_enabled=False,
        ssl_cert_file=None,
        ssl_key_file=None,
        force_https=False,
        redirect_url='https://other.example.com/',
        redirect_permanent=False,
        extra_directives=None
    )
    config = generate_redirect_vhost(vhost)
    assert 'Redirect temp "/" "https://other.example.com/"' in config


def test_generate_config_dispatcher():
    vhost = MockVhost(
        vhost_type='static',
        server_name='example.com',
        server_alias='',
        listen_port=80,
        document_root='/var/www/example.com',
        directory_options=None,
        allow_override=None,
        require_directive=None,
        error_log=None,
        custom_log=None,
        ssl_enabled=False,
        ssl_cert_file=None,
        ssl_key_file=None,
        force_https=False,
        extra_directives=None
    )
    config = generate_config(vhost)
    assert 'DocumentRoot' in config

    vhost.vhost_type = 'proxy'
    vhost.backend_protocol = 'http'
    vhost.backend_host = '127.0.0.1'
    vhost.backend_port = 8080
    vhost.backend_path = '/'
    vhost.proxy_path = '/'
    vhost.preserve_host = False
    vhost.websocket_support = False
    vhost.proxy_timeout = 300
    vhost.proxy_headers = ''
    vhost.response_headers = ''
    vhost.extra_security_headers = False
    config = generate_config(vhost)
    assert 'ProxyPass' in config

    vhost.vhost_type = 'redirect'
    vhost.redirect_url = 'https://example.com'
    vhost.redirect_permanent = True
    config = generate_config(vhost)
    assert 'Redirect' in config


def test_generate_config_unknown_type_raises():
    vhost = MockVhost(vhost_type='unknown')
    with pytest.raises(ValueError, match='Unknown vhost type'):
        generate_config(vhost)

