import requests
from bs4 import BeautifulSoup
import re
import json
import os
import sys
import csv
import time
from urllib.parse import urljoin, urlparse

def extract_course_codes(full_course_code):
    parts = full_course_code.split('-')
    return {
        "course_code": parts[0],
        "class_code": parts[1],
        "semester_code": parts[2]
    }


def extract_full_course_code(soup):
    breadcrumb_link = soup.find('a', href=re.compile('/course-profiles/.*'))
    if breadcrumb_link:
        full_course_code = breadcrumb_link['href'].split('/')[-1]
        return full_course_code
    return None


def extract_special_indicators(detail):
    indicators = []
    ul = detail.find_next('ul', class_='icon-list')
    if ul:
        for li in ul.find_all('li'):
            indicator_class = li.get('class', [])
            indicator_text = li.get_text(strip=True)
            indicators.append({
                "special_indicators_class": ' '.join(indicator_class),
                "special_indicator_text": indicator_text
            })
    return indicators


def extract_learning_outcomes(soup):
    outcomes = []
    lo_section = soup.find('section', id='learning-outcomes')
    if lo_section:
        for wrapper in lo_section.find_all('div', class_='learning-outcome-wrapper'):
            for outcome in wrapper.find_all('p'):
                strong_tag = outcome.find('strong', class_='text--primary')
                if strong_tag:
                    number = strong_tag.get_text(strip=True)
                    description = outcome.get_text(strip=True).replace(number, '').strip()
                    outcomes.append({"number": number, "description": description})
    return outcomes


def extract_assessment_details(soup):
    details_section = soup.find('section', id='assessment-details')
    details = []
    if details_section:
        for detail in details_section.find_all('h3', id=re.compile('^assessment-detail-')):
            assessment = {
                "assessment_detail_section_id": detail.get('id', ""),
                "assessment_title": detail.get_text(strip=True),
                "special_indicators": extract_special_indicators(detail),
                "weighting": detail.find_next('dt', string='Weight').find_next('dd').get_text(strip=True) if detail.find_next('dt', string='Weight') else None,
                "due_date": detail.find_next('dt', string='Due date').find_next('dd').get_text(strip=True) if detail.find_next('dt', string='Due date') else None,
                "learning_objectives": detail.find_next('dt', string='Learning outcomes').find_next('dd').get_text(strip=True) if detail.find_next('dt', string='Learning outcomes') else None,
                "mode": detail.find_next('dt', string='Mode').find_next('dd').get_text(strip=True) if detail.find_next('dt', string='Mode') else None,
                "category": detail.find_next('dt', string='Category').find_next('dd').get_text(strip=True) if detail.find_next('dt', string='Category') else None,
                "task_description": detail.find_next('h4', string='Task description').find_next('div', class_='collapsible').get_text(strip=True) if detail.find_next('h4', string='Task description') else None,
                "submission_guidelines": detail.find_next('h4', string='Submission guidelines').find_next('p').get_text(strip=True) if detail.find_next('h4', string='Submission guidelines') else None,
                "deferral_or_extension": detail.find_next('h5', string='Deferral or extension').find_next('p').get_text(strip=True) if detail.find_next('h5', string='Deferral or extension') else None,
                "late_submission": detail.find_next('h5', string='Late submission').find_next('p').get_text(strip=True) if detail.find_next('h5', string='Late submission') else None,
                # Capture any additional info in a generic way (any next h5 that hasn't been captured above)
                "additional_info": (detail.find_next('h5', string=re.compile('.*')).find_next('p').get_text(separator='\n', strip=True) 
                                 if detail.find_next('h5', string=re.compile('.*')) else None)
            }
            details.append(assessment)
    return details


def extract_learning_activities(soup):
    activities = []
    table = soup.find('table', id='table-to-filter')
    if table:
        tbody = table.find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 3:  # Ensure we have at least 3 cells
                    # Extract the learning period (week) from the first cell
                    learning_period = cells[0].get_text(strip=True)
                    
                    # Extract activity type from the second cell
                    activity_type = cells[1].get_text(strip=True)
                    
                    # Extract topic details from the third cell
                    topic_cell = cells[2]
                    topic = topic_cell.get_text(strip=True)
                    
                    # Extract topic_title from the <strong> tag within the topic cell
                    topic_title = ""
                    topic_description = ""
                    learning_outcomes = []
                    
                    # Look for the div > p > strong structure
                    div_element = topic_cell.find('div')
                    if div_element:
                        p_element = div_element.find('p')
                        if p_element:
                            strong_element = p_element.find('strong')
                            if strong_element:
                                topic_title = strong_element.get_text(strip=True)
                                
                                # Extract topic_description (text between </strong> and learning outcomes)
                                # Get all text content after the strong tag but before learning outcomes
                                remaining_content = ""
                                for content in p_element.contents:
                                    if content == strong_element:
                                        continue
                                    elif hasattr(content, 'get_text'):
                                        remaining_content += content.get_text()
                                    else:
                                        remaining_content += str(content)
                                
                                # Clean up the remaining content and look for learning outcomes
                                if remaining_content:
                                    # Split by common learning outcome indicators
                                    parts = re.split(r'(?:Learning outcomes?|LO):\s*', remaining_content, flags=re.IGNORECASE)
                                    if len(parts) > 1:
                                        topic_description = parts[0].strip()
                                        # Extract learning outcomes from the remaining parts
                                        outcomes_text = parts[1].strip()
                                        if outcomes_text:
                                            # Split learning outcomes by common separators
                                            outcomes_list = re.split(r'[,;]\s*|\s+and\s+', outcomes_text)
                                            learning_outcomes = [outcome.strip() for outcome in outcomes_list if outcome.strip()]
                                    else:
                                        topic_description = remaining_content.strip()
                    
                    # If we couldn't extract from the structured approach, try alternative methods
                    if not learning_outcomes:
                        # Look for learning outcomes in the full topic text
                        lo_match = re.search(r'(?:Learning outcomes?|LO):\s*(.+?)(?:\n|$)', topic, re.IGNORECASE | re.DOTALL)
                        if lo_match:
                            outcomes_text = lo_match.group(1).strip()
                            outcomes_list = re.split(r'[,;]\s*|\s+and\s+', outcomes_text)
                            learning_outcomes = [outcome.strip() for outcome in outcomes_list if outcome.strip()]
                    
                    # Only add if we have meaningful data
                    if learning_period and activity_type and topic:
                        activities.append({
                            "learning_period": learning_period,
                            "activity_type": activity_type,
                            "topic": topic,
                            "topic_title": topic_title,
                            "topic_description": topic_description,
                            "learning_outcomes": learning_outcomes
                        })
    return activities


def extract_semester_details(soup):
    summary_table = soup.find('section', id='course-overview--section').find('dl')
    if summary_table:
        study_period = summary_table.find('dd').get_text(strip=True)
        return study_period
    return None


def get_course_profile_links(course_code):
    """
    Get all course profile links for a given course code from the course search page
    Only returns links from the current course profiles domain (not archive)
    """
    search_url = f"https://programs-courses.uq.edu.au/course.html?course_code={course_code}"
    
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links under "Current course offerings" that point to the current course-profiles domain
        profile_links = []
        
        # Only look for links that start with the current course profiles domain
        target_domain = "https://course-profiles.uq.edu.au/course-profiles/"
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Make sure it's a full URL
            if not href.startswith('http'):
                href = urljoin(search_url, href)
            
            # Only include links from the current course profiles domain (exclude archive)
            if href.startswith(target_domain):
                profile_links.append(href)
                print(f"  Found current profile: {href}")
            elif 'archive.course-profiles.uq.edu.au' in href:
                print(f"  Skipping archived profile: {href}")
            
        return profile_links
        
    except requests.RequestException as e:
        print(f"Error fetching course search page for {course_code}: {e}")
        return []


def process_course_profile(url):
    """
    Process a single course profile URL and return the extracted data
    """
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        full_course_code = extract_full_course_code(soup)
        course_codes = extract_course_codes(full_course_code) if full_course_code else {}
        semester_details = extract_semester_details(soup)

        assessments = extract_assessment_details(soup)
        learning_outcomes = extract_learning_outcomes(soup)
        learning_activities = extract_learning_activities(soup)

        output = {
            "url": url,
            "full_course_code": full_course_code,
            **course_codes,
            "semester_details": semester_details,
            "learning_outcomes": learning_outcomes,
            "assessments": assessments,
            "learning_activities": learning_activities
        }

        return output
        
    except requests.RequestException as e:
        print(f"Error processing course profile {url}: {e}")
        return None


def save_course_data(course_data, base_directory="."):
    """
    Save course data to JSON file in the appropriate semester folder
    """
    if not course_data or not course_data.get('full_course_code'):
        return False
    
    full_course_code = course_data['full_course_code']
    semester_code = course_data.get('semester_code', '')
    
    # Create semester folder if it doesn't exist
    semester_folder = os.path.join(base_directory, semester_code)
    os.makedirs(semester_folder, exist_ok=True)
    
    # Save JSON file
    filename = f"{full_course_code}.json"
    filepath = os.path.join(semester_folder, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(course_data, f, ensure_ascii=False, indent=4)
        
        print(f"Saved data to {filepath}")
        return True
        
    except Exception as e:
        print(f"Error saving data to {filepath}: {e}")
        return False


def load_course_list(csv_filename="course-list.csv"):
    """
    Load course codes from CSV file
    Returns tuple of (included_courses, excluded_courses)
    """
    included_courses = []
    excluded_courses = []
    
    if not os.path.exists(csv_filename):
        print(f"CSV file {csv_filename} not found. Creating sample file...")
        create_sample_csv(csv_filename)
        return included_courses, excluded_courses
    
    try:
        with open(csv_filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # Skip header if present
            first_row = next(reader, None)
            if first_row and (first_row[0].lower() == 'included' or first_row[0].lower() == 'course_code'):
                pass  # Skip header
            else:
                # Process first row as data
                if first_row and len(first_row) >= 2:
                    if first_row[0].strip():
                        included_courses.append(first_row[0].strip())
                    if first_row[1].strip():
                        excluded_courses.append(first_row[1].strip())
            
            # Process remaining rows
            for row in reader:
                if len(row) >= 2:
                    if row[0].strip():
                        included_courses.append(row[0].strip())
                    if row[1].strip():
                        excluded_courses.append(row[1].strip())
                        
        print(f"Loaded {len(included_courses)} courses to include and {len(excluded_courses)} courses to exclude")
        return included_courses, excluded_courses
        
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return [], []


def create_sample_csv(filename="course-list.csv"):
    """
    Create a sample CSV file with demo course codes
    """
    demo_courses = [
        "ACCT7804", "BISM7808", "ECON7012", "FINM7805", "TIMS7811", 
        "MGTS7803", "MGTS7810", "MKTG7806", "BISM7807", "MGTS7820", 
        "MGTS7821", "MGTS7822", "MGTS7809", "MGTS7812"
    ]
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["included", "excluded"])  # Header
            
            for course in demo_courses:
                writer.writerow([course, ""])  # Add all demo courses to included column
            
            # Add a few empty rows for manual additions
            for _ in range(5):
                writer.writerow(["", ""])
                
        print(f"Created sample CSV file: {filename}")
        print("Please edit this file to specify which courses to include/exclude")
        
    except Exception as e:
        print(f"Error creating sample CSV file: {e}")


def main():
    """
    Main function to orchestrate the scraping process
    """
    print("Starting course profile scraper...")
    
    # Load course list from CSV
    included_courses, excluded_courses = load_course_list()
    
    if not included_courses:
        print("No courses found in the included list. Please check your course-list.csv file.")
        return
    
    print(f"Processing {len(included_courses)} courses...")
    print(f"Excluding {len(excluded_courses)} courses...")
    
    total_processed = 0
    total_saved = 0
    
    for course_code in included_courses:
        if course_code in excluded_courses:
            print(f"Skipping {course_code} (found in excluded list)")
            continue
            
        print(f"\nProcessing course: {course_code}")
        
        # Get all profile links for this course
        profile_links = get_course_profile_links(course_code)
        
        if not profile_links:
            print(f"No current course profile links found for {course_code}")
            continue
        
        print(f"Found {len(profile_links)} current profile link(s) for {course_code}")
        
        # Process each profile link
        for link in profile_links:
            print(f"Processing: {link}")
            
            course_data = process_course_profile(link)
            total_processed += 1
            
            if course_data:
                if save_course_data(course_data):
                    total_saved += 1
            
            # Add a small delay to be respectful to the server
            time.sleep(1)
    
    print(f"\nScraping completed!")
    print(f"Total profiles processed: {total_processed}")
    print(f"Total files saved: {total_saved}")


if __name__ == "__main__":
    main()