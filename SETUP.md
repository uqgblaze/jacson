# JacDash + JacSON Setup Guide (Raspberry Pi / Local Network)

This guide explains how to install, configure, and run JacDash on a Raspberry Pi (or any Linux machine on your home LAN), including how to create the first admin account and additional users.

---

## 1) Prerequisites

- Raspberry Pi OS / Linux with shell access
- Python 3.10+
- Network access from your LAN devices to the Pi

Check Python:

```bash
python3 --version
```

---

## 2) Get the project

From your Pi terminal:

```bash
git clone <your-repo-url> jacson
cd jacson
```

Or upload the folder manually and `cd` into it.

---

## 3) Create virtual environment and install dependencies

From project root:

```bash
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r scripts/requirements.txt
venv/bin/pip install -r jacdash/requirements.txt
```

If `venv` is missing:

```bash
sudo apt install python3-venv
```

---

## 4) Configure JacDash for local auth + LAN access

JacDash defaults to LAN-friendly host/port (`0.0.0.0:1909`) and supports local auth mode.

Set environment variables before starting:

```bash
export JACDASH_AUTH_MODE=local
export JACDASH_BOOTSTRAP_PASSWORD='change-this-to-a-strong-password'
# optional overrides:
# export JACDASH_HOST=0.0.0.0
# export JACDASH_PORT=1909
```

> `JACDASH_BOOTSTRAP_PASSWORD` is used to seed the first admin account on first startup when needed.

---

## 5) Start JacDash

```bash
cd jacdash
../venv/bin/python wsgi.py
```

JacDash listens on:

- `http://127.0.0.1:1909/` on the Pi itself
- `http://<pi-lan-ip>:1909/` from other devices on your network

Find Pi LAN IP:

```bash
hostname -I
```

Use the first IPv4 address (for example `192.168.1.55`).

---

## 6) First admin login (bootstrap)

The bootstrap username comes from `BOOTSTRAP_USER` in `jacdash/config.py`.

Current default is:

- username: `uqgblaze`
- full name: `Geoffrey Blazer`

Password is whatever you set in `JACDASH_BOOTSTRAP_PASSWORD` before startup.

Login page:

```text
http://<pi-lan-ip>:1909/login
```

After logging in, you can access the dashboard and use **Manage Users**.

---

## 7) Create additional users

### Option A (recommended): UI

1. Log in as admin.
2. Open **Manage Users**.
3. Add username and full name.

### Option B: command line (SQLite)

If you need to add users directly:

```bash
cd /path/to/jacson
sqlite3 jacdash/data/jacdash.db
```

Inside sqlite:

```sql
INSERT INTO users (uq_username, full_name, created_at, is_active, is_admin)
VALUES ('newuser', 'New User', datetime('now'), 1, 0);
```

Then quit with:

```sql
.quit
```

> Note: CLI inserts like this do not set a password hash. Use app flows/admin tooling for password management where available.

---

## 8) Promote a user to admin from command line

```bash
cd /path/to/jacson
sqlite3 jacdash/data/jacdash.db "UPDATE users SET is_admin = 1 WHERE uq_username = 'newuser';"
```

Verify:

```bash
sqlite3 jacdash/data/jacdash.db "SELECT uq_username, is_admin, is_active FROM users ORDER BY uq_username;"
```

---

## 9) Trigger JacSON from the web app

- Click **Start Manual Run** in JacDash.
- JacDash launches `run_JacSON.py`.
- Logs stream live in the terminal panel.

---

## 10) Common issues

### 403 / redirected to login

- Ensure `JACDASH_AUTH_MODE=local` is exported in the same shell where you start `wsgi.py`.
- Ensure bootstrap user exists and is active:

```bash
sqlite3 jacdash/data/jacdash.db "SELECT uq_username, is_admin, is_active FROM users;"
```

### Cannot connect from another LAN device

- Confirm app is running on `0.0.0.0:1909`.
- Confirm Pi firewall/router allows TCP 1909.
- Confirm you are using the correct Pi LAN IP.

### Forgot bootstrap/admin password

Set a new bootstrap password and restart app (if no admin password set), or update DB via CLI/admin tooling as needed.

---

## 11) Recommended production hygiene (even on home LAN)

- Use a strong `JACDASH_SECRET_KEY`.
- Use a strong `JACDASH_BOOTSTRAP_PASSWORD` and rotate it after first login.
- Do not run with Flask debug mode enabled.
- Restrict inbound access to trusted LAN segments only.

