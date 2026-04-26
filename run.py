#!/usr/bin/env python3
"""
Development entry point for Apache VHost Manager.

For production, use Gunicorn or another WSGI server.
"""

import os
from app import create_app

app = create_app(os.getenv('FLASK_CONFIG', 'default'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=app.config.get('DEBUG', True))

