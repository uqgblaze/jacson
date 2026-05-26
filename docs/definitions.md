# JacSON Course Profile — JSON Field Definitions

Each course profile is saved as a `.json` file under `profiles/{semester_code}/{full_course_code}.json`.
Fields marked **Always** are present on every profile. Fields marked **Conditional** are only written when the corresponding content exists on the source page.

---

## Top-level metadata

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `url` | string | Always | Full URL of the scraped UQ course profile page. |
| `scraped_at` | string | Always | ISO 8601 UTC timestamp of when the profile was scraped (e.g. `"2026-04-15T03:42:27.257811+00:00"`). |
| `course_code` | string | Always | Four-letter, four-digit course code (e.g. `"MGTS1301"`). |
| `class_code` | string | Always | Numeric class identifier from the profile URL (e.g. `"20352"`). |
| `semester_code` | string | Always | Numeric semester identifier from the profile URL (e.g. `"7620"`). |
| `full_course_code` | string | Always | Composite identifier used as the filename: `{course_code}-{class_code}-{semester_code}` (e.g. `"MGTS1301-20352-7620"`). |

---

## Course overview

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `course_title` | string | Always | Full course title, with any trailing parenthetical stripped (e.g. `"Introduction to Management"`). |
| `study_period` | string | Conditional | Short study period label scraped from the hero banner (e.g. `"Sem 1 2026"`). |
| `semester_details` | string | Conditional | Full study period string from the overview section, including date range (e.g. `"Semester 1, 2026 (23/02/2026 - 20/06/2026)"`). |
| `study_level` | string | Conditional | Academic level of the course (e.g. `"Undergraduate"`, `"Postgraduate"`). |
| `location` | string | Conditional | Campus or delivery location (e.g. `"St Lucia"`, `"Online"`). |
| `attendance_mode` | string | Conditional | Delivery mode as listed in the overview table (e.g. `"In Person"`, `"Online"`, `"Flexible"`). |
| `units` | string | Conditional | Credit unit value of the course (e.g. `"2"`). |
| `administrative_campus` | string | Conditional | Administrative campus responsible for the course (e.g. `"St Lucia"`). |
| `coordinating_unit` | string | Conditional | School or faculty coordinating the course (e.g. `"Business School"`). |
| `course_description` | string | Conditional | Prose description paragraphs from the course overview section. Multiple paragraphs are joined with `\n\n`. |

---

## Requirements

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `requirements` | object | Conditional | Contains one or more of the sub-keys below. Only written if any requirements content is found. |
| `requirements.prerequisites` | string[] | Conditional | List of prerequisite course codes or descriptions. |
| `requirements.incompatible` | string[] | Conditional | List of incompatible course codes. |
| `requirements.companions` | string[] | Conditional | List of companion course codes. |
| `requirements.restrictions` | string[] | Conditional | Enrolment restriction descriptions. |
| `requirements.assumed_background` | string[] | Conditional | Assumed prior knowledge or course codes. |

---

## Course contacts

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `course_contacts` | object[] | Conditional | Array of contact cards from the course contact section. |
| `course_contacts[].role` | string | Conditional | Contact's role label (e.g. `"Course coordinator"`). |
| `course_contacts[].role_slug` | string | Conditional | Lowercase, underscored version of the role for programmatic use (e.g. `"course_coordinator"`). |
| `course_contacts[].name` | string | Conditional | Contact's full name, including title if present (e.g. `"Associate Professor Sandra Figueira"`). |
| `course_contacts[].email` | string | Conditional | Contact's email address as displayed (e.g. `"s.figueira@business.uq.edu.au"`). |
| `course_contacts[].email_uri` | string | Conditional | Full `mailto:` URI for the email address. |
| `course_contacts[].phone` | string | Conditional | Contact's phone number as displayed. |
| `course_contacts[].phone_uri` | string | Conditional | Full `tel:` URI for the phone number. |
| `course_contacts[].notes_text` | string | Conditional | Plain-text content of any notes attached to the contact card. |
| `course_contacts[].notes_html` | string | Conditional | Raw HTML content of the notes element for rich rendering. |

---

## Course staff

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `course_staff` | object[] | Conditional | Array of teaching staff from the course staff section. |
| `course_staff[].role` | string | Conditional | Staff member's teaching role (e.g. `"Lecturer"`, `"Tutor"`). |
| `course_staff[].name` | string | Conditional | Staff member's full name, including title if present. |
| `course_staff[].email` | string | Conditional | Staff member's email address. |

---

## Timetable

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `timetable` | string | Conditional | Text content of the timetable section, with the section heading stripped. |

---

## Aims and learning outcomes

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `course_aims` | string | Conditional | The course aims statement. Multiple paragraphs are joined with `\n\n`. |
| `learning_outcomes` | object[] | Conditional | Ordered list of learning outcomes. |
| `learning_outcomes[].number` | string | Always (within object) | Learning outcome identifier (e.g. `"LO1."`, `"LO2."`). |
| `learning_outcomes[].description` | string | Always (within object) | Full text description of the learning outcome. |

---

## Assessments (summary)

The `assessments` array contains one entry per row from the top-level assessment summary table.

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `assessments` | object[] | Conditional | Summary-level list of assessments, as they appear in the overview table. |
| `assessments[].category` | string | Always (within object) | Assessment category (e.g. `"Examination"`, `"Paper/ Report/ Annotation"`). |
| `assessments[].assessment_title` | string | Always (within object) | Title of the assessment item. |
| `assessments[].weighting` | string | Always (within object) | Mark weighting (e.g. `"45%"`, `"20% Best 3 of 5"`). |
| `assessments[].due_date` | string | Always (within object) | Due date(s) as displayed, which may include multiple dates or a date range. |
| `assessments[].special_indicators` | object[] | Always (within object) | Array of special indicator icons. Empty array if none apply. See [Special indicators](#special-indicators). |

---

## Assessment details

The `assessment_details` array contains one entry per detailed assessment section on the page. Fields within each item are conditional on what the course profile includes.

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `assessment_details` | object[] | Conditional | Detailed breakdown of each assessment item. |
| `assessment_details[].assessment_detail_section_id` | string | Always (within object) | HTML anchor ID of the detail section, used for deep-linking (e.g. `"assessment-detail-0"`). |
| `assessment_details[].assessment_title` | string | Always (within object) | Title of the assessment item. |
| `assessment_details[].mode` | string | Conditional | Submission or delivery mode (e.g. `"Written"`, `"Oral"`, `"Product/ Artefact/ Multimedia"`). |
| `assessment_details[].category` | string | Conditional | Assessment category (matches the summary table). |
| `assessment_details[].weighting` | string | Conditional | Mark weighting (matches the summary table). |
| `assessment_details[].due_date` | string | Conditional | Due date(s) as displayed. |
| `assessment_details[].learning_objectives` | string | Conditional | Comma-separated list of learning outcome numbers assessed (e.g. `"LO1, LO2, LO3"`). |
| `assessment_details[].other_conditions` | string | Conditional | Additional conditions such as peer assessment or time limits (e.g. `"Peer assessment factor. See the conditions definitions"`). |
| `assessment_details[].task_description` | string | Conditional | Full text of the task description. |
| `assessment_details[].exam_details` | string | Conditional | Exam-specific metadata such as duration, calculator policy, and invigilation type. Present only for examination items. |
| `assessment_details[].submission_guidelines` | string | Conditional | Instructions for how and where to submit. |
| `assessment_details[].deferral_or_extension` | string | Conditional | Policy text on whether deferral or extension is permitted. |
| `assessment_details[].late_submission` | string | Conditional | Late submission penalty policy. |
| `assessment_details[].ai_statement` | string | Conditional | Extracted text relating to the permitted or prohibited use of AI tools. Only written when AI-related content is detected in the task description. |
| `assessment_details[].special_indicators` | object[] | Conditional | Array of special indicator icons. See [Special indicators](#special-indicators). |

---

## Special indicators

Special indicators appear within both `assessments[]` and `assessment_details[]` items.

| Key | Type | Description |
|-----|------|-------------|
| `special_indicators_class` | string | CSS class string from the icon list item, encoding the icon type (e.g. `"icon--how-youll-learn--multiple-circle icon-text--small"`). |
| `special_indicator_text` | string | Human-readable label for the indicator (e.g. `"Team or group-based"`, `"Identity Verified"`, `"In-person"`, `"Online"`). |

---

## Learning resources

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `learning_resources` | object | Conditional | Key-value pairs where each key is a slugified section heading and each value is the corresponding text content. Keys are dynamic and vary by course (e.g. `"library_resources"`, `"required_resources"`, `"recommended_resources"`). |

---

## Learning activities

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `learning_activities` | object[] | Conditional | Ordered list of weekly learning activities from the activities table. |
| `learning_activities[].learning_period` | string | Always (within object) | The teaching week or period label (e.g. `"Week 1"`, `"Mid-sem break"`). Carried forward from the preceding group-row for continuation rows. |
| `learning_activities[].activity_type` | string | Always (within object) | Type of activity (e.g. `"Lecture"`, `"Tutorial"`, `"No student involvement (Breaks, information)"`). |
| `learning_activities[].topic` | string | Always (within object) | Raw HTML string of the topic table cell (`<td>`), suitable for client-side parsing to extract the title and description. |
| `learning_activities[].learning_outcomes` | string[] | Conditional | List of learning outcome identifiers referenced in the topic cell (e.g. `["LO1", "LO2"]`). Only written when LO references are detected. |

---

## Policies and procedures

| Key | Type | Present | Description |
|-----|------|---------|-------------|
| `policies_and_procedures` | string | Conditional | Plain-text content of the policies and procedures section, with the section heading stripped. |
