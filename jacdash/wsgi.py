"""
wsgi.py — mod_wsgi entrypoint for JacDash on UQCloud Apache.

Apache configuration snippet (add to your VirtualHost or .conf):

    WSGIDaemonProcess jacdash python-home=/home/uqgblaze/jacdash/venv \
                                python-path=/home/uqgblaze/jacdash
    WSGIProcessGroup  jacdash
    WSGIScriptAlias   /jacdash /home/uqgblaze/jacdash/wsgi.py

    <Directory /home/uqgblaze/jacdash>
        Require all granted
    </Directory>

    <Location /jacdash>
        AuthType shibboleth
        ShibRequireSession On
        require valid-user
    </Location>

Shibboleth sets REMOTE_USER; JacDash reads it from request.environ.
"""

import sys
import os

# Ensure the jacdash directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

application = create_app()

# For local development / testing without Apache:
if __name__ == "__main__":
    application.run(debug=True, port=5050)
