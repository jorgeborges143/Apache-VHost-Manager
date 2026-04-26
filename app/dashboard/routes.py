from flask import Blueprint, render_template
from flask_login import login_required
from app.models import VirtualHost
from app.apache.service import apache_status, configtest_result
from app.apache.modules import get_module_status


dashboard_bp = Blueprint('dashboard', __name__, template_folder='../templates')


@dashboard_bp.route('/')
@login_required
def index():
    total = VirtualHost.query.count()
    enabled = VirtualHost.query.filter_by(enabled=True).count()
    disabled = total - enabled
    static_count = VirtualHost.query.filter_by(vhost_type='static').count()
    proxy_count = VirtualHost.query.filter_by(vhost_type='proxy').count()
    redirect_count = VirtualHost.query.filter_by(vhost_type='redirect').count()

    modules = get_module_status()
    apache_running = apache_status()
    configtest = configtest_result()

    return render_template(
        'dashboard.html',
        total=total,
        enabled=enabled,
        disabled=disabled,
        static_count=static_count,
        proxy_count=proxy_count,
        redirect_count=redirect_count,
        modules=modules,
        apache_running=apache_running,
        configtest=configtest
    )

