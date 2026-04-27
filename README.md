# Apache VHost Manager

A professional Bootstrap-based Flask web application for managing Apache2 virtual hosts from a browser without manually editing configuration files.

## Overview

Apache VHost Manager provides a secure, user-friendly interface for administrators to create, edit, enable, disable, and delete Apache virtual hosts. It supports static websites, reverse proxies, and redirect-only configurations with full SSL/TLS support.

## Features

- **Authentication**: Secure login/logout with password hashing and CSRF protection
- **Dashboard**: Real-time Apache status, virtual host statistics, and module monitoring
- **Virtual Host Management**:
  - Create/edit/delete static websites, reverse proxies, and redirects
  - Enable/disable sites with `a2ensite` / `a2dissite`
  - Search and filter virtual hosts
  - Download generated configurations
  - Import existing Apache configs
- **Reverse Proxy Support**: First-class support with backend testing, WebSocket support, custom headers, and security headers
- **SSL/TLS**: Full SSL configuration with optional HTTP-to-HTTPS redirect
- **Backup & Restore**: Automatic backups before edits/deletes with restore capability
- **Audit Logging**: All admin actions logged to database and file
- **Apache Module Management**: Detect and enable required modules safely
- **Security**: Path traversal protection, dangerous directive blocking, safe subprocess execution without `shell=True`

## Installation

### Prerequisites

- Ubuntu/Debian with Apache2 installed
- Python 3.9+
- pip

### Steps

1. Clone the repository:
```bash
git clone <repository-url>
cd apache-vhost-manager
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the environment file and configure:
```bash
cp .env.example .env
nano .env
```

5. Set proper permissions for Apache directories:
```bash
sudo chown -R www-data:www-data /etc/apache2/sites-available /etc/apache2/sites-enabled
```

## Configuration

Edit `.env` to configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | `dev-secret-key-change-me` |
| `ADMIN_USERNAME` | Default admin username | `admin` |
| `ADMIN_PASSWORD` | Default admin password | `admin` |
| `DATABASE_URL` | SQLite or PostgreSQL URL | `sqlite:///...` |
| `SITES_AVAILABLE_DIR` | Apache sites-available path | `/etc/apache2/sites-available` |
| `SITES_ENABLED_DIR` | Apache sites-enabled path | `/etc/apache2/sites-enabled` |
| `BACKUP_DIR` | Backup storage directory | `./backups/data` |
| `MAX_BACKUPS_PER_VHOST` | Max backups per vhost | `20` |

## Creating First Admin User

The first admin user is created automatically on startup using `ADMIN_USERNAME` and `ADMIN_PASSWORD` from `.env`. Change these before first run.

## Running in Development

```bash
source venv/bin/activate
python run.py
```

The app will be available at `http://localhost:5000`.

## Running in Production

### 1. Gunicorn Setup

```bash
source venv/bin/activate
gunicorn -c deploy/gunicorn.conf.py "app:create_app('production')"
```

### 2. systemd Setup

```bash
sudo cp systemd/apache-vhost-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable apache-vhost-manager
sudo systemctl start apache-vhost-manager
```

### 3. Nginx Reverse Proxy

```bash
sudo cp deploy/nginx-reverse-proxy.example /etc/nginx/sites-available/apache-vhost-manager
sudo ln -s /etc/nginx/sites-available/apache-vhost-manager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Apache Permissions

The app should run as a non-root user (e.g., `www-data`). Ensure the user has write access to:
- `/etc/apache2/sites-available/`
- `/etc/apache2/sites-enabled/`
- Your configured `BACKUP_DIR`
- Your configured `AUDIT_LOG_DIR`

## sudoers Configuration

The app uses `sudo` for Apache commands. Install the sudoers rules:

```bash
sudo cp deploy/sudoers.example /etc/sudoers.d/apache-vhost-manager
sudo chmod 440 /etc/sudoers.d/apache-vhost-manager
```

**Review the file before installing** to ensure the user matches your deployment.

## Security Warnings

- **Change the default admin password immediately** after first login.
- Use a strong `SECRET_KEY` in production.
- Run the app behind HTTPS in production.
- Restrict access to the admin interface by IP if possible.
- Regularly review audit logs in `AUDIT_LOG_DIR`.
- The app validates and sanitizes all inputs, but always review generated configs before enabling.

## Troubleshooting

### App cannot write to Apache directories
```bash
sudo chown -R www-data:www-data /etc/apache2/sites-available /etc/apache2/sites-enabled
```

### sudo commands fail
- Verify `/etc/sudoers.d/apache-vhost-manager` is installed and has correct permissions (`440`).
- Check that the app user matches the user in the sudoers file.
- Test manually: `sudo -u www-data sudo /usr/sbin/apache2ctl configtest`

### Database errors on first run
- Ensure the app has write permissions to the directory containing the SQLite database.
- For PostgreSQL, ensure the database and user exist.

### Config test fails after enabling a module
- The app automatically disables the module if `apache2ctl configtest` fails.
- Check Apache error logs: `sudo journalctl -u apache2`

## Backup and Restore Instructions

- Backups are created **automatically** before every edit and delete.
- View backups on the vhost detail page.
- Restore replaces the current config with the backup version.
- Old backups are automatically cleaned up based on `MAX_BACKUPS_PER_VHOST`.

## Testing

Run the test suite with pytest:

```bash
source venv/bin/activate
pytest tests/ -v
```

## License

MIT License

