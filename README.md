<p align="center">
  <img src="assets/jacson-logo-small.svg" alt="JacSON Logo" width="200"/>
</p>

# JacSON — Overview, Setup & Configuration Guide

Welcome to JacSON: a Javascript and JSON-based scraper and integration tool from UQ Jac Course Profiles into Blackboard Ultra.  
This guide explains everything that must be edited if you're adapting JacSON for another school, faculty, or institution.

## Quick Links

- View code on Github: https://github.com/uqgblaze/jacson
- Live version: 
  - Assessments preview: https://uq-business-school.github.io/jacson/demo/assessments.html
  - Weekly Activities preview: https://uq-business-school.github.io/jacson/demo/weekly-activities.html
  - Installation instructions: https://uq-business-school.github.io/jacson/demo/install.html

## Overview

JacSON automates the retrieval of learning outcomes, assessment details, and weekly learning activities from the current (non-archived) version of the UQ course profiles website. These outputs can then be used to pre-populate components in Blackboard Ultra using JavaScript, enabling a more efficient course build process for teaching teams and learning designers.

## Key Features

- **Course Intelligence**: Parses and extracts structured data such as:
  - Learning Outcomes
  - Assessment Tasks (titles, weights, dates, descriptions)
  - Weekly Activities (topics, outcomes, periods)
- **Smart Filtering**: Ignores any links to archived course profiles.
- **Local course list**: Uses a local `course-list.csv` file to determine which courses to scrape or ignore.
- **Organized Output**: Saves JSON output in folders by semester code.
- **Automatic Cloud Publishing**: Can upload JSON results to a GitHub repository.
- **Python-based and extensible**: Designed to be modular and easy to integrate with existing Python or web workflows.
- **Deploy and copy HTML to any course**: You can then copy and deploy the HTML to **any** course in Blackboard Ultra. It will automatically find the course code and find the scraped JSON file within a document.

## Limitations

- This tool is purpose-built for the **UQ JAC system** and may not generalize to other institutions without significant modification.
- Course profiles need to be written in a standardised format to benefit from this tool.
- The JSON file can only be called within a **document** on Blackboard. **This script does not work at the course-view level.**

---

## Getting Started (Raspberry Pi / Linux)

### 1. Get the project

Download the project as a ZIP, extract it, and go to the project folder (the folder that contains `run_JacSON.py` and the `scripts` folder).

### 2. Install Python and dependencies

Raspberry Pi OS uses an “externally managed” system Python, so install into a **virtual environment** in the project folder. From the **project root**:

```bash
# Create a virtual environment (once)
python3 -m venv venv

# Install dependencies into it
venv/bin/pip install -r scripts/requirements.txt
```

If `python3 -m venv` fails, install the venv package first: `sudo apt install python3-venv` (and optionally `python3-full`).

### 3. Set up your course list

Edit `course-list.csv` in the project root. It has two columns: **included** and **excluded**. Put one course code per row in the **included** column (e.g. `ACCT7804`). Leave **excluded** blank unless you want to skip specific courses.

Example:

| included | excluded |
|----------|----------|
| ACCT7804 |          |
| BISM7808 |          |

### 4. (Optional) GitHub upload

If you want the scraper to upload the generated JSON to GitHub:

1. Create a Personal Access Token on GitHub (Settings → Developer settings → Personal access tokens) with `repo` scope.
2. Create a `secrets` folder in the project root.
3. Create a file `secrets/github_token.txt` and paste the token (one line, no spaces).

If you skip this, the scraper will still run and save JSON under `profiles/`; only the upload step will be skipped or fail.

### 5. Run the scraper

From the project root, use the virtual environment’s Python:

```bash
venv/bin/python run_JacSON.py
```

For scheduled runs (e.g. daily), use cron and point it at the venv Python and full path to `run_JacSON.py` (see **Automated Controls** below).

---

## Getting Started (Windows)

### 1. Get the project

Download the repo and open the folder that contains `run_JacSON.bat` and the `scripts` folder.

### 2. Install Python

Install Python 3.10 or later from [python.org](https://www.python.org/downloads/). During install, enable **Add Python to PATH**.

Open a command prompt (CMD), go to the project folder, then:

```cmd
pip install -r scripts/requirements.txt
```

### 3. Set up your course list

Edit `course-list.csv` in the project root (included / excluded course codes as in the Pi section above).

### 4. (Optional) GitHub upload

Same as Pi: create `secrets/github_token.txt` with your GitHub Personal Access Token if you want automatic upload to a repo.

### 5. Run the scraper

Double-click `run_JacSON.bat`, or in CMD from the project folder:

```cmd
python scripts\scraper_runner.py
```

---

## Manual Controls

- To **test specific courses**: edit `course-list.csv` (included / excluded columns).
- To **run only the scraper** (no upload): from project root, `python3 scripts/jacson.py` (Linux/Pi) or `python scripts\jacson.py` (Windows). Ensure you run from the project root so `course-list.csv` and `profiles/` are found.
- To **upload only** (after scraping): `python3 scripts/upload_profiles.py` (Linux/Pi) or `python scripts\upload_profiles.py` (Windows), again from project root.

---

## Automated Controls

### Raspberry Pi / Linux — Cron

To run daily at 9:00 PM, edit crontab (`crontab -e`) and add (replace `/path/to/your/JacSON` with your real project path):

```bash
0 21 * * * /path/to/your/JacSON/venv/bin/python /path/to/your/JacSON/run_JacSON.py >> /path/to/your/JacSON/logs/cron.log 2>&1
```

### Windows — Task Scheduler

1. Create a batch file (e.g. `run_JacSON.bat`) in the project folder with:
   ```cmd
   @echo off
   cd /d "C:\Path\To\Your\JacSON"
   python scripts\scraper_runner.py
   ```
   Replace the path with your actual project path.
2. In Task Scheduler, create a basic task that runs daily and starts that batch file.

---

## Editable Configuration Overview

| What to change        | File(s)                | Location / note                    |
|-----------------------|------------------------|------------------------------------|
| GitHub repo (upload)  | `scripts/upload_profiles.py` | `GITHUB_OWNER`, `GITHUB_REPO` |
| GitHub token          | —                      | `secrets/github_token.txt`        |
| Target scrape domain | `scripts/jacson.py`    | Inside `get_course_profile_links()` |
| Output folder         | `scripts/jacson.py`    | Inside `save_course_data()`       |
| Course list file      | Several scripts        | `course-list.csv` in project root |

---

## Credits

JacSON was built by the UQ Business School Learning Design team.  
Lead developers: **Geoffrey Blazer** and **Bee Hughes**. With thanks to **Carrie Finn** for letting us cook.

---

## JacDash on Raspberry Pi 3B (LAN on port 1909)

JacDash can run on a Raspberry Pi 3B and expose the dashboard to your local network.

### Start JacDash

From the project root:

```bash
python3 -m venv venv
venv/bin/pip install -r scripts/requirements.txt
venv/bin/pip install -r jacdash/requirements.txt
cd jacdash
../venv/bin/python wsgi.py
```

By default, JacDash binds to `0.0.0.0` and port `1909`, so open:

```text
http://<pi-lan-ip>:1909/
```


### JacDash first-run admin bootstrap (Raspberry Pi / local LAN)

JacDash now checks startup for **active admin users**. If none exist, it can create one admin via environment variables:

```bash
export JACDASH_BOOTSTRAP_ADMIN_USER="uqusername:Your Name"
export JACDASH_BOOTSTRAP_ADMIN_PASSWORD="Temp-Strong-Password"
cd jacdash
../venv/bin/python wsgi.py
```

Startup log output will clearly say whether bootstrap ran.

- If bootstrap runs, remove/unset those env vars immediately after first successful login.
- Treat bootstrap credentials as **one-time-use** and rotate to a new password process straight away.
- If an active admin already exists, bootstrap is skipped.

**Recovery when admin access is lost (Pi/local):**
1. Stop JacDash.
2. Re-export `JACDASH_BOOTSTRAP_ADMIN_USER` and `JACDASH_BOOTSTRAP_ADMIN_PASSWORD` with a new temporary pair.
3. Start JacDash and confirm log: `Bootstrap admin created ...`.
4. Log in with SSO account matching the bootstrap username, then clean up/rotate and unset the variables.

### Triggering JacSON from the web dashboard

- Click **Start Manual Run** in JacDash.
- JacDash runs `run_JacSON.py` in the background.
- Live output is streamed back into the dashboard terminal panel.

This lets you run and monitor the scraper from any device on the same LAN.
