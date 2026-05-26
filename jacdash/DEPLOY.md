# JacDash — UQCloud Deployment Guide

This guide walks through deploying JacDash on a UQCloud Linux server from scratch.
It is written for someone who is not regularly working with SSH or Linux servers.

---

## What you will need before you start

- **UQCloud access** — a Linux virtual machine provisioned for your project. If you don't have one yet, raise a request through [UQ ITS](https://my.uq.edu.au/information-and-services/information-technology/information-technology-support).
- **SSH access** — your UQ username and password (or an SSH key if ITS set one up for you).
- **The JacSON project files** — the `v1.2.0` folder on your local machine.
- **Your GitHub Personal Access Token** — stored in `secrets/github_token.txt`.
- **Your Google service account credentials** — stored in `secrets/credentials.json`.

> **Note on Shibboleth (UQ SSO):** JacDash sits behind UQ's Single Sign-On system. Configuring SSO requires ITS involvement — this guide covers everything you can do yourself, and flags clearly what needs an ITS request.

---

## Part 1 — Connect to your UQCloud server

### Install an SSH client

- **Windows:** Use the built-in **Windows Terminal** or install [PuTTY](https://www.putty.org/).
- **Mac:** Use the built-in **Terminal** app.

### Connect

Replace `uqgblaze` with your UQ username and `your-server.zones.eait.uq.edu.au` with the hostname ITS gave you:

```bash
ssh uqgblaze@your-server.zones.eait.uq.edu.au
```

You'll be prompted for your UQ password. Type it and press Enter (the cursor won't move while you type — that's normal).

When you see a prompt like `uqgblaze@your-server:~$` you are connected.

> **Tip:** To disconnect at any time, type `exit` and press Enter.

---

### Creating the instance

Now need to create a webproject.
```
triton instance create --wait \
    --name uqgblaze \
    --network zones \
    --metadata uq_users=ugblaze uqsmitc6 \
    webproject \
    z1-standard
```
or
```
triton inst create --wait --name uqgblaze --network zones webproject z1-standard
```

---

### Login

```
ssh root@uqgblaze.zones.eait.uq.edu.au
```

or

```
ssh uqgblaze@uqgblaze.zones.eait.uq.edu.au
```

---

### Enable Webprojctl
Once it's been created, then check what's enabled for the ```webprojctl status```

```
webprojctl status
enabled:
available: php, uwsgi312, uwsgi314 (python), nodejs, puma (ruby / rails), jsp, tomcat (jsp / java), dotnet, mysql, postgres, redis, vscode, mongodb
```

## Part 2 — Upload the project files

You need to copy the `v1.2.0` folder from your computer to the server.
The easiest way on Windows is with **WinSCP** (free, graphical).

### Option A — WinSCP (recommended for beginners)

1. Download and install [WinSCP](https://winscp.net/eng/download.php).
2. Open WinSCP. In the login screen:
   - **File protocol:** SFTP
   - **Host name:** `your-server.zones.eait.uq.edu.au`
   - **User name:** `uqgblaze`
   - **Password:** your UQ password
3. Click **Login**.
4. On the right panel, navigate to `/home/uqgblaze/`.
5. On the left panel, navigate to the `v1.2.0` folder on your computer.
6. Drag the entire `v1.2.0` folder from left to right to upload it.

After uploading, your server should have:
```
/home/uqgblaze/v1.2.0/
    jacdash/
    scripts/
    course-list.csv
    secrets/
    profiles/
    logs/
    ...
```

### Option B — scp from the terminal (advanced)

From your local machine (not the server), run:
```bash
scp -r "C:/Users/geoff/OneDrive - .../v1.2.0" uqgblaze@your-server.zones.eait.uq.edu.au:/home/uqgblaze/
```

---

## Part 3 — Set up Python on the server

Back in your SSH terminal:

### 3.1 — Check Python is available

```bash
python3 --version
```

You need Python 3.10 or newer. If it shows an older version or "command not found", contact ITS to have a suitable Python installed.

### 3.2 — Create a virtual environment

A virtual environment keeps JacSON's Python packages isolated from the rest of the server.

```bash
cd /home/uqgblaze/v1.2.0
python3 -m venv venv
```

If this fails with a message about `venv` not being available:
```bash
sudo apt install python3-venv
python3 -m venv venv
```

### 3.3 — Install dependencies

```bash
venv/bin/pip install --upgrade pip
venv/bin/pip install -r scripts/requirements.txt
venv/bin/pip install flask pytz
```

This may take a minute or two. You'll see a list of packages being downloaded and installed.

### 3.4 — Verify the install

```bash
venv/bin/python -c "import flask; print('Flask', flask.__version__)"
```

You should see something like `Flask 3.1.0`.

---

## Part 4 — Set file permissions

The web server (Apache) runs as a different user (`www-data`). JacDash needs to be able to write to its `data/` and `logs/` directories.

```bash
cd /home/uqgblaze/v1.2.0

# Make sure the logs and data directories exist
mkdir -p jacdash/data jacdash/logs logs

# Give Apache write access to the directories JacDash writes to
chmod -R 775 jacdash/data jacdash/logs logs profiles
chown -R uqgblaze:www-data jacdash/data jacdash/logs logs profiles
```
## PERSONAL NOTE: Ran into an issue
Error:
chown: invalid group: `uqgblaze:ww-data`

> **What this does:** `775` lets the owner (you) and the group (`www-data` = Apache) read and write. `chown` makes `www-data` the group owner of those directories.

---

## Part 5 — Update config.py

Open the config file in the server's text editor:

```bash
nano /home/uqgblaze/v1.2.0/jacdash/config.py
```

Check that `JACSON_ROOT` resolves correctly. You can verify by running:

```bash
venv/bin/python -c "import sys; sys.path.insert(0,'jacdash'); import config; print(config.JACSON_ROOT)"
```

It should print `/home/uqgblaze/v1.2.0`.

Also set a strong secret key. In `nano`, find the line:
```python
SECRET_KEY = os.environ.get("JACDASH_SECRET_KEY", "change-me-in-production")
```
and change `"change-me-in-production"` to a long random string, for example:
```python
SECRET_KEY = os.environ.get("JACDASH_SECRET_KEY", "j8Kx2mQ9vLpR5nYw3oBt7cAeZdHuNfGs")
```

To save and exit `nano`: press `Ctrl+O`, then Enter, then `Ctrl+X`.

---

## Part 6 — Test the app manually

Before touching Apache, confirm the app starts:

```bash
cd /home/uqgblaze/v1.2.0/jacdash
FLASK_DEBUG=1 JACDASH_DEV_USER=uqgblaze ../venv/bin/python wsgi.py
```

You should see:
```
 * Running on http://127.0.0.1:5050
```

Press `Ctrl+C` to stop it. If you see any Python errors here, fix them before continuing.

---

## Part 7 — Configure Apache

Apache serves JacDash to the web. You'll need **sudo access** for this section — if you don't have it, send the configuration snippet to ITS and ask them to apply it.

### 7.1 — Install mod_wsgi

```bash
sudo apt install libapache2-mod-wsgi-py3
sudo a2enmod wsgi
```

### 7.2 — Create an Apache config file

```bash
sudo nano /etc/apache2/sites-available/jacdash.conf
```

Paste the following (adjust paths if your username or server setup differs):

```apache
<VirtualHost *:443>
    ServerName your-server.zones.eait.uq.edu.au

    # ── JacDash WSGI app ────────────────────────────────────────────
    WSGIDaemonProcess jacdash \
        python-home=/home/uqgblaze/v1.2.0/venv \
        python-path=/home/uqgblaze/v1.2.0/jacdash \
        user=uqgblaze group=www-data \
        threads=5
    WSGIProcessGroup  jacdash
    WSGIScriptAlias   /jacdash /home/uqgblaze/v1.2.0/jacdash/wsgi.py

    <Directory /home/uqgblaze/v1.2.0/jacdash>
        Require all granted
    </Directory>

    # ── Static files served directly by Apache (faster) ────────────
    Alias /jacdash/static /home/uqgblaze/v1.2.0/jacdash/static
    <Directory /home/uqgblaze/v1.2.0/jacdash/static>
        Require all granted
    </Directory>

    # ── UQ SSO (Shibboleth) — protect the entire /jacdash path ─────
    # ITS will configure the Shibboleth block. Leave a placeholder:
    <Location /jacdash>
        AuthType shibboleth
        ShibRequireSession On
        require valid-user
    </Location>

    # Shibboleth metadata endpoint (required by SSO)
    <Location /Shibboleth.sso>
        SetHandler shib
    </Location>

    # ── SSL certificates ────────────────────────────────────────────
    # ITS typically manages certificates on UQCloud. If not pre-configured:
    # SSLEngine on
    # SSLCertificateFile    /etc/ssl/certs/your-cert.pem
    # SSLCertificateKeyFile /etc/ssl/private/your-key.pem

    ErrorLog  /var/log/apache2/jacdash-error.log
    CustomLog /var/log/apache2/jacdash-access.log combined
</VirtualHost>
```

Save and exit (`Ctrl+O`, Enter, `Ctrl+X`).

### 7.3 — Enable the site and reload Apache

```bash
sudo a2ensite jacdash.conf
sudo apache2ctl configtest
```

The `configtest` must say `Syntax OK`. If it shows errors, read them carefully — they usually point to a typo in the config.

```bash
sudo systemctl reload apache2
```

---

## Part 8 — Request Shibboleth (SSO) from ITS

> **This step requires an ITS request.** You cannot configure Shibboleth yourself.

Email ITS (or raise a ticket at [my.uq.edu.au](https://my.uq.edu.au)) with the following information:

---
**Subject:** Shibboleth SSO for JacDash application on UQCloud

Hi ITS,

I have a Flask web application (JacDash) running on [your-server.zones.eait.uq.edu.au] that needs to be protected by UQ Single Sign-On (Shibboleth).

- **Application URL:** `https://your-server.zones.eait.uq.edu.au/jacdash`
- **Auth type required:** Shibboleth, with `REMOTE_USER` set to the authenticated UQ username
- **Access scope:** UQ staff only (small number of specific users managed in-app)
- **Apache config:** already in place at `/etc/apache2/sites-available/jacdash.conf` with a `<Location /jacdash>` Shibboleth block

Could you please configure the Shibboleth service provider on this server and advise when it is ready to test?

---

Once ITS confirms SSO is active, remove the `JACDASH_DEV_USER` workaround if you added it to any production config.

---

## Part 9 — Set up the cron job

The cron scheduler checks every minute whether it's time to run JacSON automatically.

```bash
crontab -e
```

If asked to choose an editor, type `1` (nano) and press Enter.

At the bottom of the file, add this line:

```
* * * * * /home/uqgblaze/v1.2.0/venv/bin/python /home/uqgblaze/v1.2.0/jacdash/cron_scheduler.py >> /home/uqgblaze/v1.2.0/jacdash/logs/cron.log 2>&1
```

Save and exit (`Ctrl+O`, Enter, `Ctrl+X`). Cron will confirm: `crontab: installing new crontab`.

To verify it was saved:
```bash
crontab -l
```

---

## Part 10 — Verify the deployment

### Check Apache is running

```bash
sudo systemctl status apache2
```

Look for `Active: active (running)`. If it says `failed`, check the error log:
```bash
sudo tail -50 /var/log/apache2/jacdash-error.log
```

### Check the app responds

From your browser (once SSO is configured), visit:
```
https://your-server.zones.eait.uq.edu.au/jacdash
```

You should be redirected to the UQ login page, and then land on the JacDash control panel.

### Check the cron log

After a minute has passed:
```bash
tail -20 /home/uqgblaze/v1.2.0/jacdash/logs/cron.log
```

You should see lines like:
```
2026-04-15 03:00:01 [cron] INFO: Checking schedule: time=03:00 days=Mon,Tue,Wed,Thu,Fri
2026-04-15 03:00:01 [cron] INFO: Not scheduled to run now. Exiting.
```

---

## Updating JacDash after changes

When you make changes locally and want to push them to the server:

1. Upload the changed files via WinSCP (overwrite the existing files).
2. Reload Apache to pick up any Python changes:
   ```bash
   sudo systemctl reload apache2
   ```

You do **not** need to restart the cron job — it re-reads the script every minute automatically.

---

## Quick reference: useful SSH commands

| Task | Command |
|---|---|
| Check Apache status | `sudo systemctl status apache2` |
| Reload Apache | `sudo systemctl reload apache2` |
| View Apache error log | `sudo tail -50 /var/log/apache2/jacdash-error.log` |
| View cron log | `tail -50 /home/uqgblaze/v1.2.0/jacdash/logs/cron.log` |
| View latest scrape log | `ls -lt /home/uqgblaze/v1.2.0/logs/` then `cat` the newest file |
| Edit cron schedule | `crontab -e` |
| Open a file in nano | `nano /path/to/file` |
| Save in nano | `Ctrl+O` then Enter |
| Exit nano | `Ctrl+X` |
| Disconnect SSH | `exit` |
