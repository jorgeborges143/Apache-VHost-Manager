"""
Basic Apache Virtual Host Configuration Parser

Extracts key directives from existing Apache vhost config files.
Unsupported directives are collected and shown in a read-only advanced section.
"""

import re
from collections import defaultdict


def parse_vhost_config(content):
    """
    Parse Apache config text and return a dict of extracted fields.
    """
    result = defaultdict(lambda: None)
    result['server_alias'] = []
    result['proxy_pass'] = []
    result['proxy_pass_reverse'] = []
    result['request_header'] = []
    result['header'] = []
    result['unsupported_directives'] = []

    # Extract VirtualHost blocks
    vhost_blocks = re.findall(r'<VirtualHost[^>]*>(.*?)</VirtualHost>', content, re.DOTALL | re.IGNORECASE)
    if not vhost_blocks:
        return dict(result)

    # Use the first block for primary extraction
    block = vhost_blocks[0]

    simple_directives = {
        'ServerName': 'server_name',
        'DocumentRoot': 'document_root',
        'ErrorLog': 'error_log',
        'CustomLog': 'custom_log',
        'SSLCertificateFile': 'ssl_cert_file',
        'SSLCertificateKeyFile': 'ssl_key_file',
        'Redirect': 'redirect',
    }

    for directive, key in simple_directives.items():
        pattern = re.compile(rf'^\s*{directive}\s+(.*?)$', re.MULTILINE | re.IGNORECASE)
        match = pattern.search(block)
        if match:
            result[key] = match.group(1).strip().split()[0] if key != 'redirect' else match.group(1).strip()

    # ServerAlias (multiple)
    for match in re.finditer(r'^\s*ServerAlias\s+(.*?)$', block, re.MULTILINE | re.IGNORECASE):
        aliases = match.group(1).strip().split()
        result['server_alias'].extend(aliases)

    # ProxyPass / ProxyPassReverse
    for match in re.finditer(r'^\s*ProxyPass\s+(.*?)\s+(.*?)$', block, re.MULTILINE | re.IGNORECASE):
        result['proxy_pass'].append({'path': match.group(1).strip(), 'url': match.group(2).strip()})
    for match in re.finditer(r'^\s*ProxyPassReverse\s+(.*?)\s+(.*?)$', block, re.MULTILINE | re.IGNORECASE):
        result['proxy_pass_reverse'].append({'path': match.group(1).strip(), 'url': match.group(2).strip()})

    # RequestHeader
    for match in re.finditer(r'^\s*RequestHeader\s+(.*?)$', block, re.MULTILINE | re.IGNORECASE):
        result['request_header'].append(match.group(1).strip())

    # Header
    for match in re.finditer(r'^\s*Header\s+(.*?)$', block, re.MULTILINE | re.IGNORECASE):
        result['header'].append(match.group(1).strip())

    # SSL detection
    result['ssl_enabled'] = 'SSLEngine on' in block or re.search(r'SSLEngine\s+on', block, re.IGNORECASE) is not None

    # Force HTTPS detection
    result['force_https'] = re.search(r'RewriteRule.*https://', block, re.IGNORECASE) is not None

    # Detect vhost type
    if result['proxy_pass']:
        result['vhost_type'] = 'proxy'
    elif result.get('redirect'):
        result['vhost_type'] = 'redirect'
    else:
        result['vhost_type'] = 'static'

    # Collect unsupported directives for advanced view
    known = set(simple_directives.keys()) | {'ServerAlias', 'ProxyPass', 'ProxyPassReverse',
                                              'RequestHeader', 'Header', 'SSLEngine', 'SSLCertificateFile',
                                              'SSLCertificateKeyFile', 'RewriteEngine', 'RewriteCond',
                                              'RewriteRule', 'ProxyPreserveHost', 'ProxyTimeout',
                                              '<Directory', '</Directory>', 'Options', 'AllowOverride',
                                              'Require', '<VirtualHost', '</VirtualHost>'}
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        directive_name = stripped.split()[0]
        if directive_name not in known and directive_name not in result['unsupported_directives']:
            result['unsupported_directives'].append(stripped)

    return dict(result)

