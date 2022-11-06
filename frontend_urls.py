"""
URLs that point to the frontend but are needed in the backend.

Please note the following:
1. It's important to keep this module updated
2. Please don't rename any variables
3. Tests are likely to fail after changes, fix them before deployment
4. Omit leading slashes
"""


# Pages

PAGE = '{slug}/'

# NOTE: If you change these URLs you have to update them on Newsletter2Go, too

LEGAL_NOTICE = 'about/'

PRIVACY = 'privacy/'


# Auth

LOGIN = 'auth/login/'

LOGOUT = 'auth/logout/'

EMAIL_CONFIRMATION = r'^auth/confirm-email/(?P<key>[-:\w]+)/$'

PASSWORD_RESET = (
    r'^auth/password-reset-confirmation/'
    r'(?P<uidb64>[0-9A-Za-z_\-]+)/'
    r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$'
)


# NOTE: If you change this URL you have to update the callback URL
# in the OAuth providers' accounts, too
OAUTH_CALLBACK = 'auth/social/{provider}/callback/'


# Development

STATIC_FILES = r'^(?P<path>(img|js|css|favicon)/.+|.+\.(js(on)?|txt|ico|html))$'


# Other

SEGMENT = (
    'editor/{work_language}/{work_id}/chapter/{chapter}/'
    'paragraph/{position_in_chapter}/'
)

DEVELOPER_COMMENTS = 'roadmap/'
