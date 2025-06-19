<p align="center">
  <img src="jacson-logo-small.svg" alt="JacSON Logo" width="200"/>
</p>

# JacSON

**JacSON** (Jac Scraper Output for Navigation) is a Python-based utility designed to scrape course profiles from the University of Queensland's JAC system and export structured JSON data suitable for integration into Blackboard Ultra.

## Overview

JacSON automates the retrieval of learning outcomes, assessment details, and weekly learning activities from the current (non-archived) version of the UQ course profiles website. These outputs can then be used to pre-populate components in Blackboard Ultra using JavaScript, enabling a more efficient course build process for teaching teams and learning designers.

## Key Features

- 🧠 **Course Intelligence**: Parses and extracts structured data such as:
  - Learning Outcomes
  - Assessment Tasks (titles, weights, dates, descriptions)
  - Weekly Activities (topics, outcomes, periods)
- ⛔ **Smart Filtering**: Ignores any links to archived course profiles.
- 📝 **Course List Control**: Uses a local `course-list.csv` file to determine which courses to scrape or ignore.
- 🗃️ **Organized Output**: Saves JSON output in folders by semester code.
- 🧪 **Python-based and extensible**: Designed to be modular and easy to integrate with existing Python or web workflows.

## Usage

1. Ensure you have Python 3 and the following dependencies installed:
   - `requests`
   - `beautifulsoup4`

2. Edit or create a `course-list.csv` file with two columns: `included` and `excluded`. This determines which courses JacSON will attempt to scrape.

3. Run the script:
   ```bash
   python jacson_v7.py
   ```

4. Output files will be saved as `.json` in folders named after the course's semester code.

## Upcoming Features

We are currently developing a fully automated workflow to support:

- ✅ **Integration with Google Sheets**: Automatically fetch course codes to include/exclude.
- ⚙️ **Scheduled GitHub Actions**: Trigger JacSON to run daily/weekly based on Google Sheets toggles (e.g., “JacSON Request” column).
- ☁️ **Cloud-first publishing**: Upload JSON outputs directly to GitHub for integration with other tools.

## Limitations

- Only the **current live profiles** are scraped — archived versions are explicitly skipped.
- Currently a **manual workflow** — full automation is under development.
- This tool is purpose-built for the **UQ JAC system** and may not generalize without modification.

## Repository Structure

```text
.
├── jacson_v7.py          # Main scraper logic
├── course-list.csv       # Input course control file
├── jacson-logo-small.svg # JacSON logo
├── README.md             # Project documentation (you are here)
└── <semester_code>/      # Output folders, e.g. 2430/, 2410/
    └── MGTS7812-001-2430.json
```

## Contributing

This is an internal tool designed to streamline learning design workflows. Contributions are welcome via pull requests or issue reports.

## License

This project is provided under the [MIT License](LICENSE).

---

Made with 🧠 by the UQ Business School Learning Design Team.
