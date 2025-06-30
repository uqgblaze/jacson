function getQueryParam(param) {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get(param);
}

async function loadAssessments() {
  const jsonPath = getQueryParam('json');
  const fullPath = jsonPath ? `${jsonPath}.json` : null;

  if (!fullPath) {
    document.getElementById('content').innerHTML =
      '<p class="error">Error: Course profile not yet published, or broken link to course profile.</p>';
    return;
  }

  try {
    const response = await fetch(fullPath);
    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);

    const data = await response.json();
    const semester = data.semester_details || 'Assessment Details';
    const coursecode = data.course_code || 'Course Code';
    const assessments = data.assessments;

    if (!assessments || assessments.length === 0) {
      document.getElementById('content').innerHTML =
        '<p class="error">No assessments found in the JSON file.</p>';
      return;
    }

    let tableHtml = `
      <table>
        <caption>${coursecode}: ${semester}</caption>
        <thead>
          <tr>
            <th>Title</th>
            <th class="center">Weighting</th>
            <th class="center">Due Date</th>
            <th class="center">Learning Objectives</th>
          </tr>
        </thead>
        <tbody>
    `;

    assessments.forEach(a => {
      const title = a.assessment_title || '—';
      const weighting = a.weighting || '—';
      const dueDate = a.due_date || '—';
      const learningObjectives = a.learning_objectives || '—';

      tableHtml += `
        <tr id="${a.assessment_detail_section_id || ''}">
          <td>${title}</td>
          <td class="center">${weighting}</td>
          <td class="center">${dueDate}</td>
          <td class="center">${learningObjectives}</td>
        </tr>
      `;
    });

    tableHtml += '</tbody></table>';

    // Inject the instructional message if the domain matches
    const currentHost = window.location.hostname;
    if (["learn.uq.edu.au", "saas-stage.learn.uq.edu.au"].includes(currentHost)) {
      tableHtml += `<p class="jacson-preload">Click on the "Save" button to finish inserting the Assessment Overview table</p>`;
    }

    document.getElementById('content').innerHTML = tableHtml;

  } catch (error) {
    document.getElementById('content').innerHTML =
      `<p class="error">Failed to load JSON: ${error.message}</p>`;
  }
}

loadAssessments();
