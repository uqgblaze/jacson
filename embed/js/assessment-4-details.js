    // Dynamic assessment details controller
    (function () {
      const allowedDomains = [
        "learn.uq.edu.au",
        "saas-stage.learn.uq.edu.au"
      ];
      const currentHost = window.location.hostname;

      // PREVIEW INSTRUCTION ONLY
      if (allowedDomains.includes(currentHost)) {
        const preloadMessage = document.createElement("p");
        preloadMessage.className = "jacson-preload";
        preloadMessage.textContent = 'Click on the "Save" button at the top-right to finish inserting the Assessment Details';
        document.body.appendChild(preloadMessage);
        return; // Stop further execution
      }

      // PRODUCTION BEHAVIOUR (CDN delivery with full functionality)
      document.addEventListener('DOMContentLoaded', async () => {
        const url = window.location.href;
        const loadingState = document.getElementById('loadingState');
        const errorState = document.getElementById('errorState');
        const mainContent = document.getElementById('mainContent');

        try {
          // Extract course code and assessment index from URL
          const match = url.match(/\/courses\/([^\/]+)\//);
          if (!match) {
            throw new Error('Course code not detected in URL');
          }

          const fullCourseCode = match[1];  // e.g. "BSAN7209_7560_60200"
          const [courseCode, semesterCode, classCode] = fullCourseCode.split('_');
          
          if (!courseCode || !semesterCode || !classCode) {
            throw new Error('Invalid course code format');
          }

          // Try to extract assessment index from URL or filename
          // This could be from URL parameters, hash, or filename pattern
          let assessmentIndex = 4; // Default to first assessment
          // Assessment 1 = assessmentIndex = 0, 
          // Assessment 2 = assessmentIndex = 1,
          // Assessment 3 = assessmentIndex = 2, etc.
          
          // Check for assessment index in URL hash or search params
          const urlParams = new URLSearchParams(window.location.search);
          const hashMatch = window.location.hash.match(/assessment-(\d+)/);
          const paramIndex = urlParams.get('assessment');
          
          if (hashMatch) {
            assessmentIndex = parseInt(hashMatch[1]);
          } else if (paramIndex) {
            assessmentIndex = parseInt(paramIndex);
          } else {
            // Try to extract from filename pattern (e.g., assessment-details-0_v001.html)
            const filenameMatch = window.location.pathname.match(/assessment-details-(\d+)/);
            if (filenameMatch) {
              assessmentIndex = parseInt(filenameMatch[1]);
            }
          }

          // Construct JSON path
          const jsonPath = `https://uqgblaze.github.io/jacson/profiles/${semesterCode}/${courseCode}-${classCode}-${semesterCode}.json`;
          
          // Fetch course data
          const response = await fetch(jsonPath);
          if (!response.ok) {
            throw new Error(`Failed to fetch course data: ${response.status}. This course currently does not have a publicly available course profile, and/or the course profile has not yet been processed by JacSON.`);
          }
          
          const courseData = await response.json();
          
          // Check if assessment exists
          if (!courseData.assessments || !courseData.assessments[assessmentIndex]) {
            throw new Error(`Assessment ${assessmentIndex} not found in course data. This course does not appear to have an assessment with this index. Please check the URL or try a different assessment index.`);
          }
          
          // Render the assessment data
          renderAssessmentData(courseData.assessments[assessmentIndex], assessmentIndex);
          
          // Show main content and hide loading
          loadingState.classList.add('hidden');
          mainContent.classList.remove('hidden');
          
        } catch (error) {
          console.error('Error loading assessment data:', error);
          loadingState.classList.add('hidden');
          errorState.classList.remove('hidden');
          errorState.querySelector('p').textContent = `Error: ${error.message}`;
        }
      });

      function renderAssessmentData(assessment, index) {
        // Set assessment ID (hidden)
        document.getElementById('assessmentId').textContent = `assessment_detail_section_id_${index}`;

        // Set assessment title
        document.getElementById('assessmentTitle').textContent = assessment.assessment_title;

        // Render special indicators
        const specialIndicators = document.getElementById('specialIndicators');
        specialIndicators.innerHTML = '';
        if (assessment.special_indicators && assessment.special_indicators.length > 0) {
          assessment.special_indicators.forEach(indicator => {
            const li = document.createElement('li');
            
            // Create span element for the icon
            const iconSpan = document.createElement('span');
            
            // Set the proper UQ icon classes using special_indicators_class
            const iconClass = indicator.special_indicators_class || '';
            iconSpan.className = `uq-icon uq-icon--light uq-${iconClass}`;
            
            // Add text content
            const textNode = document.createTextNode(indicator.special_indicator_text);
            
            // Append icon and text to li
            li.appendChild(iconSpan);
            li.appendChild(textNode);
            
            specialIndicators.appendChild(li);
          });
        }

        // Populate table data
        document.getElementById('mode').textContent = assessment.mode || 'N/A';
        document.getElementById('category').textContent = assessment.category || 'N/A';
        
        // Clean up weighting
        const weighting = assessment.weighting ? assessment.weighting.replace(/<\/?dd>/g, '') : 'N/A';
        document.getElementById('weighting').textContent = weighting;
        
        // Clean up and highlight due date
        const dueDate = assessment.due_date ? assessment.due_date.replace(/<\/?dd>|<\/?p>/g, '').trim() : 'N/A';
        const dueDateElement = document.getElementById('dueDate');
        dueDateElement.innerHTML = `<span class="due-date">${dueDate}</span>`;
        
        document.getElementById('learningObjectives').textContent = assessment.learning_objectives || 'N/A';

        // Populate sections
        populateSection('taskDescription', assessment.task_description);
        populateSection('submissionGuidelines', assessment.submission_guidelines);
        populateSection('deferralOrExtension', assessment.deferral_or_extension);
        populateSection('lateSubmission', assessment.late_submission);
      }

      function populateSection(elementId, content) {
        const element = document.getElementById(elementId);
        if (content) {
          // Clean up any collapsible wrapper HTML that might be present
          let cleanContent = content
            .replace(/<div class="collapsible[^>]*>/, '')
            .replace(/<button class="collapsible__toggle"[\s\S]*?<\/button>/, '')
            .replace(/<\/div>$/, '');
          
          element.innerHTML = cleanContent;
        } else {
          element.innerHTML = '<p><em>No information available, and/or or this course profile is not yet public, and/or or this course profile has not yet been compiled by JacSON.</em></p>';
        }
      }
    })();