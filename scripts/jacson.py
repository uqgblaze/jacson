#!/usr/bin/env python3
"""
jacson.py  —  JacSON course profile scraper
============================================
Scrapes the full content of UQ course profile pages from
course-profiles.uq.edu.au and saves each profile as a JSON file under:

    ./profiles/<semester_code>/<full_course_code>.json

Course list is read from course-list.csv (two columns: included, excluded).

Scraping engine based on the enriched scraper by Sean Smith (UQBS),
integrated into the JacSON Pi architecture by Geoff Blaze (UQ Course Profiles).
"""

import csv
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}

PROGRAMS_COURSES_BASE = "https://programs-courses.uq.edu.au"
COURSE_PROFILES_BASE = "https://course-profiles.uq.edu.au"

REQUEST_DELAY = 1.0   # seconds between requests
REQUEST_TIMEOUT = 30  # seconds

log = logging.getLogger("jacson")


# ---------------------------------------------------------------------------
# Course list (CSV)
# ---------------------------------------------------------------------------

def load_course_list(csv_path: str = "course-list.csv") -> tuple[list[str], list[str]]:
    """
    Read included and excluded course codes from a two-column CSV.

    Expected columns: included, excluded  (header row is skipped if present).
    Returns (included_courses, excluded_courses).
    """
    included: list[str] = []
    excluded: list[str] = []

    if not os.path.exists(csv_path):
        log.warning(f"course-list.csv not found at {csv_path}. Creating sample file.")
        _create_sample_csv(csv_path)
        return included, excluded

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            first_row = next(reader, None)
            if first_row:
                # Skip header if first cell looks like a header label
                if first_row[0].strip().lower() not in ("included", "course_code"):
                    _append_csv_row(first_row, included, excluded)
            for row in reader:
                _append_csv_row(row, included, excluded)
    except Exception as e:
        log.error(f"Error reading {csv_path}: {e}")

    log.info(f"Loaded {len(included)} included / {len(excluded)} excluded courses")
    return included, excluded


def _append_csv_row(row: list[str], included: list, excluded: list):
    if len(row) >= 1 and row[0].strip():
        included.append(row[0].strip())
    if len(row) >= 2 and row[1].strip():
        excluded.append(row[1].strip())


def _create_sample_csv(path: str):
    sample = ["ACCT7804", "BISM7808", "ECON7012"]
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["included", "excluded"])
            for code in sample:
                w.writerow([code, ""])
        log.info(f"Created sample CSV at {path}")
    except Exception as e:
        log.error(f"Could not create sample CSV: {e}")


# ---------------------------------------------------------------------------
# Discovery: find profile URLs via programs-courses.uq.edu.au
# ---------------------------------------------------------------------------

def get_course_profile_links(course_code: str) -> list[str]:
    """
    Return live (non-archived) course profile URLs for a given course code
    by scraping the UQ programs-courses search page.
    """
    search_url = f"{PROGRAMS_COURSES_BASE}/course.html?course_code={course_code}"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"  Could not fetch search page for {course_code}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    target_prefix = f"{COURSE_PROFILES_BASE}/course-profiles/"
    links: list[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("http"):
            href = f"{PROGRAMS_COURSES_BASE}{href}"
        if href.startswith(target_prefix):
            links.append(href)
        elif "archive.course-profiles.uq.edu.au" in href:
            log.debug(f"  Skipping archived profile: {href}")

    return links


# ---------------------------------------------------------------------------
# Full-page scraper
# ---------------------------------------------------------------------------

def scrape_profile(url: str) -> dict | None:
    """
    Fetch and parse a single course profile page.
    Returns an enriched dict, or None on network failure.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"  Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    profile: dict = {
        "url": url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }

    _extract_course_codes(soup, profile)
    _extract_overview(soup, profile)
    _extract_course_description(soup, profile)
    _extract_requirements(soup, profile)
    _extract_contacts(soup, profile)
    _extract_staff(soup, profile)
    _extract_timetable(soup, profile)
    _extract_aims(soup, profile)
    _extract_learning_outcomes(soup, profile)
    _extract_assessment(soup, profile)
    _extract_learning_resources(soup, profile)
    _extract_learning_activities(soup, profile)
    _extract_policies(soup, profile)

    return profile


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_course_codes(soup: BeautifulSoup, profile: dict):
    """Extract course/class/semester codes from breadcrumb or URL."""
    pattern = re.compile(r"/course-profiles/([A-Z]{4}\d{4})-(\d+)-(\d{4})")

    # Try breadcrumb links first
    for a in soup.select("a[href*='/course-profiles/']"):
        m = pattern.search(a.get("href", ""))
        if m:
            profile["course_code"] = m.group(1)
            profile["class_code"] = m.group(2)
            profile["semester_code"] = m.group(3)
            profile["full_course_code"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            return

    # Fallback: parse from URL
    m = pattern.search(profile.get("url", ""))
    if m:
        profile["course_code"] = m.group(1)
        profile["class_code"] = m.group(2)
        profile["semester_code"] = m.group(3)
        profile["full_course_code"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def _extract_overview(soup: BeautifulSoup, profile: dict):
    """
    Extract the course overview summary table.

    Produces two study-period fields:
      study_period     — short label scraped from hero banner, e.g. "Sem 1 2025"
      semester_details — full string from overview section, e.g. "Semester 1, 2025 (24/02/2025 - 21/06/2025)"
    """
    section = (
        soup.find(id="course-overview--section")
        or soup.find(id="course-overview")
    )
    if not section:
        return

    # Short study_period from hero banner (e.g. "Sem 1 2025")
    hero = soup.find("div", class_="hero__text")
    if hero:
        dl = hero.find("dl", class_="hero__course-offerings")
        if dl:
            for div in dl.find_all("div", class_="hero__course-offering"):
                dt = div.find("dt")
                dd = div.find("dd")
                if dt and dd and dt.get_text(strip=True).lower() == "study period":
                    profile["study_period"] = dd.get_text(strip=True)
                    break

    # Course title from <h1>
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(separator=" ", strip=True)
        title = re.sub(r"\s*\([^)]*\)\s*$", "", title)
        profile["course_title"] = title

    field_map = {
        "Study period":          None,          # handled specially below
        "Study level":           "study_level",
        "Location":              "location",
        "Attendance mode":       "attendance_mode",
        "Units":                 "units",
        "Administrative campus": "administrative_campus",
        "Coordinating unit":     "coordinating_unit",
    }

    for dt in section.find_all("dt"):
        label = dt.get_text(separator=" ", strip=True)
        if label not in field_map:
            continue
        dd = dt.find_next_sibling("dd")
        if not dd:
            continue
        value = dd.get_text(separator=" ", strip=True)

        if label == "Study period":
            profile["semester_details"] = value
        else:
            profile[field_map[label]] = value


def _extract_course_description(soup: BeautifulSoup, profile: dict):
    """
    Extract the prose paragraphs that appear after the summary table
    in the course overview section (course description, SDG notes, etc.).
    """
    section = soup.find(id="course-overview--section")
    if not section:
        return

    highlight = section.find(class_="highlight")
    if not highlight:
        return

    parts: list[str] = []
    sibling = highlight.find_next_sibling()
    while sibling:
        if sibling.name in ("h2", "section"):
            break
        if sibling.name in ("p", "div"):
            text = sibling.get_text(separator=" ", strip=True)
            if text and len(text) > 10:
                parts.append(text)
        sibling = sibling.find_next_sibling()

    if parts:
        profile["course_description"] = "\n\n".join(parts)


def _extract_requirements(soup: BeautifulSoup, profile: dict):
    """
    Extract prerequisites, incompatibles, companions, assumed background, etc.
    from the course-requirements section.
    """
    section = soup.find(id="course-requirements")
    if not section:
        return

    requirements: dict[str, list[str]] = {}
    current_label: str | None = None

    for child in section.descendants:
        if isinstance(child, NavigableString):
            continue
        text = child.get_text(separator=" ", strip=True)
        if child.name in ("h3", "h4", "strong"):
            lower = text.lower()
            if "prerequisite" in lower:
                current_label = "prerequisites"
            elif "incompatible" in lower:
                current_label = "incompatible"
            elif "companion" in lower:
                current_label = "companions"
            elif "restriction" in lower:
                current_label = "restrictions"
            elif "assumed" in lower or "background" in lower:
                current_label = "assumed_background"
        elif current_label and child.name in ("p", "dd", "li", "span"):
            if text:
                codes = re.findall(r"[A-Z]{4}\d{4}", text)
                if codes:
                    requirements.setdefault(current_label, []).extend(codes)
                elif text not in requirements.get(current_label, []):
                    requirements.setdefault(current_label, []).append(text)

    # Deduplicate each list
    requirements = {k: list(dict.fromkeys(v)) for k, v in requirements.items()}

    # Simple fallback
    if not requirements:
        full_text = section.get_text(separator=" ", strip=True)
        codes = re.findall(r"[A-Z]{4}\d{4}", full_text)
        if codes:
            requirements["incompatible"] = list(dict.fromkeys(codes))

    if requirements:
        profile["requirements"] = requirements


def _extract_contacts(soup: BeautifulSoup, profile: dict):
    """
    Extract course contacts (coordinator, etc.) from #course-contact.

    Preserves role_slug for indexson.py compatibility.
    """
    section = soup.find(id="course-contact")
    if not section:
        return

    contacts: list[dict] = []
    seen: set = set()

    for card in section.select(".contact-card, article"):
        contact: dict = {}

        role_el = card.select_one(".contact-card__role-heading, h3")
        if role_el:
            role = role_el.get_text(separator=" ", strip=True)
            contact["role"] = role
            # Generate role_slug for indexson.py compatibility
            slug = role.lower().strip().replace("&", "and").replace("/", " ")
            slug = re.sub(r"[^a-z0-9\s]", "", slug)
            slug = re.sub(r"\s+", "_", slug)
            contact["role_slug"] = slug

        name_el = card.select_one(".contact-card__name, .contact-card__details")
        if name_el:
            contact["name"] = name_el.get_text(separator=" ", strip=True)

        email_el = card.select_one(".contact-card__email a, a[href^='mailto:']")
        if email_el:
            contact["email"] = email_el.get_text(separator=" ", strip=True)
            contact["email_uri"] = email_el.get("href", "").strip()

        phone_el = card.select_one(".contact-card__phone a, a[href^='tel:']")
        if phone_el:
            contact["phone"] = phone_el.get_text(separator=" ", strip=True)
            contact["phone_uri"] = phone_el.get("href", "").strip()

        notes_el = card.select_one(".contact-card__notes")
        if notes_el:
            contact["notes_text"] = notes_el.get_text(separator=" ", strip=True)
            contact["notes_html"] = str(notes_el).strip()

        key = (
            contact.get("role", ""),
            contact.get("name", ""),
            contact.get("email", ""),
        )
        if key not in seen and any(contact.values()):
            seen.add(key)
            contacts.append(contact)

    if contacts:
        profile["course_contacts"] = contacts


def _extract_staff(soup: BeautifulSoup, profile: dict):
    """
    Extract all teaching staff from #course-staff.

    Each role heading (h3.staff-cards__role) is followed by a
    .staff-cards__cards div containing one or more contact-card articles.
    """
    section = soup.find(id="course-staff")
    if not section:
        return

    staff: list[dict] = []
    seen: set = set()

    for role_heading in section.select("h3.staff-cards__role"):
        role = role_heading.get_text(separator=" ", strip=True)
        cards_div = role_heading.find_next_sibling("div", class_="staff-cards__cards")
        if not cards_div:
            continue

        for card in cards_div.select("article.contact-card"):
            person: dict = {"role": role}

            name_el = card.select_one(".contact-card__name")
            if name_el:
                person["name"] = name_el.get_text(separator=" ", strip=True)

            email_el = card.select_one("a[href^='mailto:']")
            if email_el:
                person["email"] = email_el.get_text(separator=" ", strip=True)

            key = (person.get("name", ""), person.get("role", ""))
            if key not in seen and any(person.values()):
                seen.add(key)
                staff.append(person)

    if staff:
        profile["course_staff"] = staff


def _extract_timetable(soup: BeautifulSoup, profile: dict):
    """Extract the timetable section text."""
    section = soup.find(id="timetable")
    if not section:
        return
    text = section.get_text(separator="\n", strip=True)
    text = re.sub(r"^Timetable\s*", "", text).strip()
    if text:
        profile["timetable"] = text


def _extract_aims(soup: BeautifulSoup, profile: dict):
    """
    Extract the course aims statement from #aim-and-outcomes--section.

    Handles both Layout A (aims in <p> tags) and Layout B (bare text nodes).
    """
    section = (
        soup.find(id="aim-and-outcomes--section")
        or soup.find(id="aim-and-outcomes")
    )
    if not section:
        return

    parts: list[str] = []
    for child in section.children:
        # Stop when we hit the learning outcomes sub-section
        if child.name == "section":
            break
        if isinstance(child, NavigableString):
            text = child.strip()
            if text and len(text) > 10:
                parts.append(text)
            continue
        if child.name in ("h2", "h3"):
            continue
        if child.name in ("p", "div"):
            text = child.get_text(separator=" ", strip=True)
            if text and text.lower() != "aims and outcomes" and len(text) > 10:
                parts.append(text)

    if parts:
        profile["course_aims"] = "\n\n".join(parts)


def _extract_learning_outcomes(soup: BeautifulSoup, profile: dict):
    """
    Extract learning outcomes (number + description).

    Handles two page layouts:
      Layout A: LO number and description in the same <p>
      Layout B: LO number in one <p>, description in the next <p>
    """
    section = soup.find(id="learning-outcomes")
    if not section:
        return

    outcomes: list[dict] = []

    lo_strongs = section.find_all("strong", string=re.compile(r"^LO\d+\.?$"))

    if lo_strongs:
        for strong in lo_strongs:
            number = strong.get_text(separator=" ", strip=True)
            description = ""
            parent_p = strong.find_parent("p")

            # Layout A: description in the same <p>
            if parent_p:
                full_text = parent_p.get_text(separator=" ", strip=True)
                same_p_desc = re.sub(r"^LO\d+\.?\s*", "", full_text).strip()
                if same_p_desc:
                    description = same_p_desc

            # Layout B: description in the next sibling <p>
            if not description and parent_p:
                sibling = parent_p.find_next_sibling()
                while sibling:
                    if sibling.name == "p":
                        text = sibling.get_text(separator=" ", strip=True)
                        if text and not re.match(r"^LO\d+\.?\s*$", text):
                            description = text
                            break
                    sibling = sibling.find_next_sibling()

            description = re.sub(r"^LO\d+\.?\s*", "", description).strip()
            if description:
                outcomes.append({"number": number, "description": description})

    # Regex fallback
    if not outcomes:
        text = section.get_text()
        for num, desc in re.findall(
            r"(LO\d+\.?)\s*(.+?)(?=LO\d+\.|$)", text, re.DOTALL
        ):
            desc_clean = desc.strip()
            if desc_clean:
                outcomes.append({"number": num.strip(), "description": desc_clean})

    if outcomes:
        profile["learning_outcomes"] = outcomes


def _extract_assessment(soup: BeautifulSoup, profile: dict):
    """
    Extract both the assessment summary table and the detailed items.

    Also extracts special_indicators per detail item for indexson.py
    compatibility (group_assessment and hurdle detection).
    """
    section = soup.find(id="assessment")
    if not section:
        return

    # --- Summary table ---
    summary: list[dict] = []
    summary_table = None
    for tbl in section.find_all("table"):
        if not tbl.find_parent(id=re.compile(r"assessment-detail")):
            summary_table = tbl
            break

    if summary_table:
        for row in summary_table.select("tbody tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            title_link = cells[1].find("a")
            title = (
                title_link.get_text(separator=" ", strip=True)
                if title_link
                else cells[1].get_text(separator=" ", strip=True)
            )

            # Special indicators (icon-list items in title cell)
            indicators: list[dict] = []
            icon_list = cells[1].find("ul", class_="icon-list")
            if icon_list:
                for li in icon_list.find_all("li"):
                    indicators.append({
                        "special_indicators_class": " ".join(li.get("class", [])),
                        "special_indicator_text": li.get_text(separator=" ", strip=True),
                    })

            item: dict = {
                "category": cells[0].get_text(separator=" ", strip=True),
                "assessment_title": title,
                "weighting": cells[2].get_text(separator=" ", strip=True),
                "due_date": cells[3].get_text(separator="; ", strip=True),
                "special_indicators": indicators,
            }
            summary.append(item)

    if summary:
        profile["assessments"] = summary  # named "assessments" for indexson.py

    # --- Detailed items ---
    details: list[dict] = []
    for h3 in section.select("h3[id^='assessment-detail-']"):
        item: dict = {
            "assessment_detail_section_id": h3.get("id", ""),
            "assessment_title": h3.get_text(separator=" ", strip=True),
        }

        # Collect sibling elements scoped to this h3
        scoped: list = []
        sibling = h3.find_next_sibling()
        while sibling:
            if (
                sibling.name == "h3"
                and sibling.get("id", "").startswith("assessment-detail")
            ):
                break
            scoped.append(sibling)
            sibling = sibling.find_next_sibling()

        # Build a temp container
        temp = Tag(name="div")
        for el in scoped:
            temp.append(el.__copy__())

        _extract_assessment_detail_fields(temp, item)
        details.append(item)

    if details:
        profile["assessment_details"] = details


def _extract_assessment_detail_fields(container: Tag, item: dict):
    """Extract all fields from a scoped assessment detail container."""
    # DT/DD pairs (Mode, Category, Weight, Due date, etc.)
    _FIELD_MAP = {
        "Mode": "mode",
        "Category": "category",
        "Weight": "weighting",
        "Due date": "due_date",
        "Learning outcomes": "learning_objectives",
        "Other conditions": "other_conditions",
        "Task description": "task_description",
        "Submission guidelines": "submission_guidelines",
        "Deferral or extension": "deferral_or_extension",
        "Late submission": "late_submission",
    }

    for dt in container.find_all("dt"):
        label = dt.get_text(separator=" ", strip=True)
        key = _FIELD_MAP.get(label)
        if key:
            dd = dt.find_next_sibling("dd")
            if dd:
                item[key] = dd.get_text(separator=" ", strip=True)

    # H4 subheadings with content blocks
    for h4 in container.find_all("h4"):
        label = h4.get_text(separator=" ", strip=True)
        key = _FIELD_MAP.get(label)
        if not key:
            key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        if not key:
            continue
        parts: list[str] = []
        sib = h4.find_next_sibling()
        while sib and sib.name not in ("h3", "h4"):
            text = sib.get_text(separator=" ", strip=True)
            if text:
                parts.append(text)
            sib = sib.find_next_sibling()
        if parts:
            item[key] = "\n".join(parts)

    # H5 subsections (Deferral, Late submission)
    for h5 in container.find_all("h5"):
        label = h5.get_text(separator=" ", strip=True)
        key = _FIELD_MAP.get(label)
        if not key:
            key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
        sib = h5.find_next_sibling()
        if sib and sib.name in ("p", "div"):
            item[key] = sib.get_text(separator=" ", strip=True)

    # AI statement detection
    full_text = container.get_text()
    if re.search(r"artificial intelligence|generative ai|\bAI\b", full_text, re.I):
        ai_parts: list[str] = []
        for el in container.find_all(["p", "li", "div"]):
            el_text = el.get_text(separator=" ", strip=True)
            if re.search(
                r"artificial intelligence|generative ai|use of AI|AI tools|AI writing",
                el_text, re.I
            ) and len(el_text) > 20 and el_text not in ai_parts:
                ai_parts.append(el_text)
        if ai_parts:
            item["ai_statement"] = "\n".join(ai_parts)

    # Special indicators (icon-list)
    indicators: list[dict] = []
    for icon_list in container.select(".icon-list"):
        for li in icon_list.find_all("li"):
            indicators.append({
                "special_indicators_class": " ".join(li.get("class", [])),
                "special_indicator_text": li.get_text(separator=" ", strip=True),
            })
    if indicators:
        item["special_indicators"] = indicators


def _extract_learning_resources(soup: BeautifulSoup, profile: dict):
    """Extract the learning resources section."""
    section = soup.find(id="learning-resources")
    if not section:
        return

    resources: dict = {}
    for heading in section.find_all(["h3", "h4"]):
        heading_text = heading.get_text(separator=" ", strip=True).lower()
        parts: list[str] = []
        sib = heading.find_next_sibling()
        while sib and sib.name not in ("h2", "h3"):
            text = sib.get_text(separator=" ", strip=True)
            if text:
                parts.append(text)
            sib = sib.find_next_sibling()
        if parts:
            key = re.sub(r"[^a-z0-9]+", "_", heading_text).strip("_")
            resources[key] = "\n".join(parts)

    if not resources:
        text = section.get_text(separator=" ", strip=True)
        text = re.sub(r"^Learning resources\s*", "", text).strip()
        if text:
            resources["text"] = text

    if resources:
        profile["learning_resources"] = resources


def _extract_learning_activities(soup: BeautifulSoup, profile: dict):
    """
    Extract the weekly learning activities table.
    Handles both 3-column rows (new learning period) and 2-column continuation rows.
    """
    section = soup.find(id="learning-activities")
    if not section:
        return

    table = section.find("table", id="table-to-filter") or section.find("table")
    if not table:
        return

    activities: list[dict] = []
    current_period = ""

    for row in table.select("tbody tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        activity: dict = {}

        if len(cells) >= 3 and "course-table__new-group" in cells[0].get("class", []):
            current_period = cells[0].get_text(separator=" ", strip=True)
            activity["learning_period"] = current_period
            activity["activity_type"] = cells[1].get_text(separator=" ", strip=True)
            topic_cell = cells[2]
        elif len(cells) >= 2:
            activity["learning_period"] = current_period
            activity["activity_type"] = cells[0].get_text(separator=" ", strip=True)
            topic_cell = cells[1]
        else:
            continue

        activity["topic"] = str(topic_cell).strip()

        # Extract LO references from topic text
        lo_matches = re.findall(r"LO?\d+", topic_cell.get_text())
        if lo_matches:
            activity["learning_outcomes"] = list(dict.fromkeys(lo_matches))

        if activity.get("topic"):
            activities.append(activity)

    if activities:
        profile["learning_activities"] = activities


def _extract_policies(soup: BeautifulSoup, profile: dict):
    """Extract the policies and procedures section text."""
    section = soup.find(id="policies-and-guidelines")
    if not section:
        return
    text = section.get_text(separator=" ", strip=True)
    text = re.sub(r"^Policies and procedures\s*", "", text).strip()
    if text:
        profile["policies_and_procedures"] = text


# ---------------------------------------------------------------------------
# Whitespace normalisation
# ---------------------------------------------------------------------------

_WS_RUN = re.compile(r"[ \t\u00A0]+")
_NL_RUN = re.compile(r"\n{3,}")


def _normalise_ws(value):
    """Recursively collapse whitespace in all strings in a JSON-compatible tree."""
    if isinstance(value, str):
        s = value.replace("\u00A0", " ")
        s = _WS_RUN.sub(" ", s)
        s = "\n".join(line.strip(" \t") for line in s.split("\n"))
        s = _NL_RUN.sub("\n\n", s)
        return s.strip()
    if isinstance(value, list):
        return [_normalise_ws(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalise_ws(v) for k, v in value.items()}
    return value


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def save_course_data(course_data: dict, base_directory: str = ".") -> bool:
    """
    Save a scraped profile under:
      {base_directory}/profiles/{semester_code}/{full_course_code}.json

    Returns True on success, False on failure.
    """
    if not course_data or not course_data.get("full_course_code"):
        return False

    full_code = course_data["full_course_code"]
    semester_code = course_data.get("semester_code", "").strip()

    semester_dir = Path(base_directory) / "profiles" / semester_code
    semester_dir.mkdir(parents=True, exist_ok=True)

    filepath = semester_dir / f"{full_code}.json"

    course_data = _normalise_ws(course_data)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(course_data, f, ensure_ascii=False, indent=4)
        log.info(f"  Saved {filepath}")
        return True
    except Exception as e:
        log.error(f"  Error saving {filepath}: {e}")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(csv_path: str = "course-list.csv", base_directory: str = ".") -> dict:
    """
    Load course list from CSV, scrape each course profile, and save to disk.
    Returns a results dict keyed by course code.
    """
    log.info("Starting JacSON scraper...")

    included, excluded = load_course_list(csv_path)
    if not included:
        log.warning("No courses in included list — check course-list.csv")
        return {}

    excluded_set = set(excluded)
    results: dict = {}

    for course_code in included:
        if course_code in excluded_set:
            log.info(f"Skipping {course_code} (excluded)")
            continue

        log.info(f"Processing {course_code}")
        links = get_course_profile_links(course_code)

        if not links:
            log.warning(f"  No profile links found for {course_code}")
            results[course_code] = {"success": False, "note": "No profile links found"}
            continue

        success = False
        for link in links:
            log.info(f"  Scraping {link}")
            data = scrape_profile(link)
            if data:
                if save_course_data(data, base_directory):
                    success = True
            time.sleep(REQUEST_DELAY)

        results[course_code] = {
            "success": success,
            "note": "" if success else "Profile found but failed to save",
        }

    log.info("Scraping complete.")
    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    main()
