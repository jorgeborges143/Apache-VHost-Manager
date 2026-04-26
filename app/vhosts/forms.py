from flask_wtf import FlaskForm
from wtforms import (
    StringField, IntegerField, TextAreaField, BooleanField,
    SelectField, FieldList, FormField, SubmitField
)
from wtforms.validators import DataRequired, Optional, NumberRange, Regexp, Length
import re


DOMAIN_REGEX = re.compile(
    r'^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$'
)

SAFE_PATH_REGEX = re.compile(r'^[a-zA-Z0-9_\-/\.]+$')
SAFE_FILENAME_REGEX = re.compile(r'^[a-zA-Z0-9_\-]+$')


class AliasForm(FlaskForm):
    alias = StringField('Alias', validators=[DataRequired(), Regexp(DOMAIN_REGEX, message='Invalid domain name')])


class HeaderForm(FlaskForm):
    key = StringField('Header Name', validators=[DataRequired(), Length(max=128)])
    value = StringField('Header Value', validators=[DataRequired(), Length(max=512)])


class VirtualHostForm(FlaskForm):
    vhost_type = SelectField(
        'Virtual Host Type',
        choices=[
            ('static', 'Static Website'),
            ('proxy', 'Reverse Proxy'),
            ('redirect', 'Redirect Only')
        ],
        validators=[DataRequired()]
    )
    server_name = StringField(
        'ServerName',
        validators=[
            DataRequired(),
            Regexp(DOMAIN_REGEX, message='Invalid domain name.')
        ]
    )
    server_alias = FieldList(StringField('Alias'), min_entries=0, max_entries=10)
    listen_port = IntegerField(
        'Listen Port',
        default=80,
        validators=[DataRequired(), NumberRange(min=1, max=65535)]
    )

    # SSL
    ssl_enabled = BooleanField('Enable SSL')
    ssl_cert_file = StringField('SSL Certificate File', validators=[Optional()])
    ssl_key_file = StringField('SSL Certificate Key File', validators=[Optional()])
    force_https = BooleanField('Force HTTP to HTTPS Redirect')

    # Static
    document_root = StringField('DocumentRoot', validators=[Optional()])
    directory_options = SelectField(
        'Directory Options',
        choices=[
            ('', 'None'),
            ('Indexes FollowSymLinks', 'Indexes FollowSymLinks'),
            ('FollowSymLinks', 'FollowSymLinks'),
            ('Indexes', 'Indexes'),
            ('All', 'All')
        ],
        default='Indexes FollowSymLinks',
        validators=[Optional()]
    )
    allow_override = SelectField(
        'AllowOverride',
        choices=[
            ('', 'None'),
            ('All', 'All'),
            ('None', 'None (explicit)')
        ],
        validators=[Optional()]
    )
    require_directive = StringField('Require Directive', default='all granted', validators=[Optional()])

    # Proxy
    backend_protocol = SelectField(
        'Backend Protocol',
        choices=[('http', 'HTTP'), ('https', 'HTTPS')],
        default='http'
    )
    backend_host = StringField('Backend Host', default='127.0.0.1', validators=[Optional()])
    backend_port = IntegerField(
        'Backend Port',
        default=8080,
        validators=[Optional(), NumberRange(min=1, max=65535)]
    )
    backend_path = StringField('Backend Base Path', default='/', validators=[Optional()])
    proxy_path = StringField('Public Proxy Path', default='/', validators=[Optional()])
    preserve_host = BooleanField('Preserve Host Header')
    websocket_support = BooleanField('WebSocket Support')
    proxy_timeout = IntegerField('Proxy Timeout (seconds)', default=300, validators=[Optional(), NumberRange(min=1)])
    request_headers = FieldList(FormField(HeaderForm), min_entries=0, max_entries=10)
    response_headers = FieldList(FormField(HeaderForm), min_entries=0, max_entries=10)
    extra_security_headers = BooleanField('Add Extra Security Headers')

    # Redirect
    redirect_url = StringField('Destination URL', validators=[Optional()])
    redirect_permanent = BooleanField('Permanent Redirect (301)')

    # Logs
    error_log = StringField('ErrorLog Path', validators=[Optional()])
    custom_log = StringField('CustomLog Path', validators=[Optional()])

    # Advanced
    extra_directives = TextAreaField('Additional Directives', validators=[Optional()])

    submit = SubmitField('Save Virtual Host')

    def validate_document_root(self, field):
        if self.vhost_type.data == 'static' and field.data:
            if '..' in field.data or not SAFE_PATH_REGEX.match(field.data):
                raise ValueError('Invalid or unsafe DocumentRoot path.')

    def validate_ssl_cert_file(self, field):
        if self.ssl_enabled.data and field.data:
            if '..' in field.data or not SAFE_PATH_REGEX.match(field.data):
                raise ValueError('Invalid SSL certificate path.')

    def validate_ssl_key_file(self, field):
        if self.ssl_enabled.data and field.data:
            if '..' in field.data or not SAFE_PATH_REGEX.match(field.data):
                raise ValueError('Invalid SSL key path.')

    def validate_error_log(self, field):
        if field.data:
            if '..' in field.data or not SAFE_PATH_REGEX.match(field.data):
                raise ValueError('Invalid log path.')

    def validate_custom_log(self, field):
        if field.data:
            if '..' in field.data or not SAFE_PATH_REGEX.match(field.data):
                raise ValueError('Invalid log path.')

    def validate_extra_directives(self, field):
        if field.data:
            blocked = ['exec', 'shell', 'cgi', 'suexec', 'mod_perl', 'mod_python',
                       'AddHandler', 'Action', 'ScriptAlias', 'CGIDScriptTimeout']
            for directive in blocked:
                if directive in field.data:
                    raise ValueError(f'Directive "{directive}" is not allowed for security reasons.')

