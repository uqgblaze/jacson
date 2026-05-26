/* JacSON Course Profile Viewer — app.js
 *
 * Shared helpers + page controllers. Vanilla JS, no build step.
 *
 * Data sources (all absolute, served from GitHub Pages):
 *   BASE_URL/profiles/index.json          -- lean index of all profiles
 *   BASE_URL/profiles/{sem}/{code}.json   -- full profile JSON (loaded on demand)
 *
 * Field names follow the jacson.py scraper output:
 *   assessments          -- summary table rows (category, assessment_title, weighting, due_date)
 *   assessment_details   -- full detail items (adds mode, learning_objectives, task_description, …)
 *   learning_outcomes    -- [{number, description}]  (number already contains "LO" prefix)
 *   learning_activities  -- [{learning_period, activity_type, topic, learning_outcomes}]
 */

const BASE_URL   = "https://uq-course-profiles.github.io/jacson";
const INDEX_URL  = `${BASE_URL}/profiles/index.json`;

// ---------------------------------------------------------------------------
// Shared state
// ---------------------------------------------------------------------------
const STORE = { index: null };

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------
async function loadIndex() {
  if (STORE.index) return STORE.index;
  const res = await fetch(INDEX_URL, { cache: "no-cache" });
  if (!res.ok) throw new Error(`Could not load course index: ${res.status}`);
  STORE.index = await res.json();
  return STORE.index;
}

async function loadCourseJson(relPath) {
  // relPath is e.g. "profiles/7520/ACCT7804-22499-7520.json"
  const url = `${BASE_URL}/${relPath}`;
  const res = await fetch(url, { cache: "no-cache" });
  if (!res.ok) throw new Error(`Could not load ${relPath}: ${res.status}`);
  return res.json();
}

function getAllCourses(index) {
  // indexson.py produces a flat "courses" array, already sorted
  return index.courses || [];
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------
function uniqueSorted(values) {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) =>
    String(a).localeCompare(String(b))
  );
}

function escapeHtml(s) {
  if (s == null) return "";
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function coursePrefix(code) {
  if (!code) return "";
  const m = String(code).match(/^([A-Z]{3,4})/);
  return m ? m[1] : "";
}

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-AU", {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

// ---------------------------------------------------------------------------
// Export helpers
// ---------------------------------------------------------------------------
function htmlToText(html) {
  if (!html) return "";
  let t = String(html);
  t = t.replace(/<br\s*\/?>/gi, "\n").replace(/<\/p>/gi, "\n\n")
       .replace(/<\/li>/gi, "\n").replace(/<\/div>/gi, "\n")
       .replace(/<[^>]+>/g, "");
  t = t.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
       .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, " ");
  return t.replace(/\n{3,}/g, "\n\n").trim();
}

function htmlToMarkdown(html) {
  if (!html) return "";
  let md = String(html);
  md = md.replace(/<strong>([\s\S]*?)<\/strong>/gi, "**$1**")
         .replace(/<b>([\s\S]*?)<\/b>/gi, "**$1**")
         .replace(/<em>([\s\S]*?)<\/em>/gi, "*$1*")
         .replace(/<i>([\s\S]*?)<\/i>/gi, "*$1*")
         .replace(/<a\s+href="([^"]*)"[^>]*>([\s\S]*?)<\/a>/gi, "[$2]($1)")
         .replace(/<li>([\s\S]*?)<\/li>/gi, "- $1\n")
         .replace(/<\/p>/gi, "\n\n").replace(/<br\s*\/?>/gi, "\n")
         .replace(/<[^>]+>/g, "");
  md = md.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
         .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, " ");
  return md.replace(/\n{3,}/g, "\n\n").trim();
}

function stripLoSuffix(topic) {
  return String(topic || "").replace(/\s*Learning outcomes?:.*$/i, "").trim();
}

function safeFilename(c, ext) {
  const parts = [c.course_code, c.class_code, c.semester_code].filter(Boolean);
  return `${parts.join("-") || "course"}.${ext}`;
}

function downloadBlob(content, filename, mimeType) {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  URL.revokeObjectURL(url);
}

// Render a special_indicators value from jacson.py.
// Each item is either a string (legacy) or {special_indicators_class, special_indicator_text}.
function indicatorText(ind) {
  if (!ind) return "";
  if (typeof ind === "string") return ind;
  return ind.special_indicator_text || "";
}

// Build a Markdown document from a full course JSON.
function buildCourseMarkdown(c) {
  const lines = [];
  lines.push(`# ${c.course_code} — ${c.course_title || ""}`, "");

  const metaRows = [
    ["Full code",            c.full_course_code],
    ["Study period",         c.study_period],
    ["Study level",          c.study_level],
    ["Units",                c.units],
    ["Attendance mode",      c.attendance_mode],
    ["Location",             c.location],
    ["Coordinating unit",    c.coordinating_unit],
    ["Administrative campus",c.administrative_campus],
    ["Course profile URL",   c.url],
    ["Scraped",              c.scraped_at],
  ].filter(([, v]) => v);
  for (const [k, v] of metaRows) lines.push(`- **${k}:** ${v}`);

  if (c.course_description) {
    lines.push("", "## Course description", "", htmlToMarkdown(c.course_description));
  }
  if (c.course_aims) {
    lines.push("", "## Course aims", "", htmlToMarkdown(c.course_aims));
  }

  if (c.requirements && typeof c.requirements === "object") {
    const hasAny = Object.values(c.requirements).some(v => v && (Array.isArray(v) ? v.length : String(v).trim()));
    if (hasAny) {
      lines.push("", "## Requirements");
      for (const [key, label] of [
        ["prerequisites",    "Prerequisites"],
        ["incompatible",     "Incompatible courses"],
        ["companions",       "Companions"],
        ["restrictions",     "Restrictions"],
        ["assumed_background","Assumed background"],
      ]) {
        const v = c.requirements[key];
        if (!v) continue;
        const items = Array.isArray(v) ? v : [v];
        if (!items.length) continue;
        lines.push("", `**${label}**`, "");
        for (const item of items) lines.push(`- ${String(item)}`);
      }
    }
  }

  if (Array.isArray(c.learning_outcomes) && c.learning_outcomes.length) {
    lines.push("", "## Learning outcomes", "");
    for (const lo of c.learning_outcomes) {
      // jacson.py: {number: "LO1.", description: "..."}  — number already has "LO" prefix
      lines.push(`- **${lo.number || ""}** ${lo.description || ""}`);
    }
  }

  // Assessment summary table (jacson.py key: "assessments")
  if (Array.isArray(c.assessments) && c.assessments.length) {
    lines.push("", "## Assessment summary", "");
    lines.push("| # | Task | Category | Weight | Due |");
    lines.push("|---|------|----------|--------|-----|");
    c.assessments.forEach((a, i) => {
      const title = (a.assessment_title || "").replace(/\|/g, "/");
      const cat   = (a.category || "").replace(/\|/g, "/");
      const w     = (a.weighting || "").replace(/\|/g, "/");
      const due   = (a.due_date || "").replace(/\|/g, "/");
      lines.push(`| ${i + 1} | ${title} | ${cat} | ${w} | ${due} |`);
    });
  }

  // Assessment details (jacson.py key: "assessment_details")
  if (Array.isArray(c.assessment_details) && c.assessment_details.length) {
    lines.push("", "## Assessment details", "");
    c.assessment_details.forEach((a, i) => {
      lines.push(`### ${i + 1}. ${a.assessment_title || "Assessment"}`, "");
      const meta = [];
      if (a.weighting)          meta.push(`**Weight:** ${a.weighting}`);
      if (a.due_date)           meta.push(`**Due:** ${a.due_date}`);
      if (a.category)           meta.push(`**Category:** ${a.category}`);
      if (a.mode)               meta.push(`**Mode:** ${a.mode}`);
      if (a.other_conditions)   meta.push(`**Conditions:** ${a.other_conditions}`);
      if (meta.length) { lines.push(meta.join(" · ")); lines.push(""); }

      if (a.learning_objectives) {
        lines.push(`**Linked LOs:** ${a.learning_objectives}`, "");
      }
      if (Array.isArray(a.special_indicators) && a.special_indicators.length) {
        lines.push(`**Indicators:** ${a.special_indicators.map(indicatorText).join(", ")}`, "");
      }
      for (const [key, label] of [
        ["task_description",    "Task description"],
        ["submission_guidelines","Submission guidelines"],
        ["deferral_or_extension","Deferral or extension"],
        ["late_submission",     "Late submission"],
        ["ai_statement",        "AI / academic integrity"],
      ]) {
        const v = a[key];
        if (!v) continue;
        lines.push(`#### ${label}`, "");
        lines.push(htmlToMarkdown(String(v)));
        lines.push("");
      }
      lines.push("---", "");
    });
  }

  if (Array.isArray(c.learning_activities) && c.learning_activities.length) {
    lines.push("", "## Weekly learning activities", "");
    lines.push("| Period | Type | Topic | LOs |");
    lines.push("|--------|------|-------|-----|");
    for (const la of c.learning_activities) {
      const period = (la.learning_period || "").replace(/\|/g, "/").replace(/\n/g, " ");
      const type   = (la.activity_type   || "").replace(/\|/g, "/");
      const topic  = stripLoSuffix(la.topic).replace(/\|/g, "/").replace(/\n/g, " ");
      const los    = Array.isArray(la.learning_outcomes)
                       ? la.learning_outcomes.join(", ")
                       : (la.learning_outcomes || "");
      lines.push(`| ${period} | ${type} | ${topic} | ${los} |`);
    }
  }

  if (c.learning_resources && typeof c.learning_resources === "object") {
    const entries = Object.entries(c.learning_resources).filter(([, v]) => v);
    if (entries.length) {
      lines.push("", "## Learning resources", "");
      for (const [k, v] of entries) {
        const label = k.replace(/_/g, " ").replace(/\b\w/g, s => s.toUpperCase());
        lines.push(`**${label}**`, "");
        lines.push(Array.isArray(v) ? v.map(x => `- ${x}`).join("\n") : htmlToMarkdown(String(v)));
        lines.push("");
      }
    }
  } else if (typeof c.learning_resources === "string" && c.learning_resources.trim()) {
    lines.push("", "## Learning resources", "", htmlToMarkdown(c.learning_resources));
  }

  if (c.timetable) {
    lines.push("", "## Timetable", "", htmlToMarkdown(String(c.timetable)));
  }

  if (Array.isArray(c.course_contacts) && c.course_contacts.length) {
    lines.push("", "## Course contacts", "");
    for (const s of c.course_contacts) {
      lines.push(`- ${[s.name, s.role, s.email].filter(Boolean).join(" — ")}`);
    }
  }
  if (Array.isArray(c.course_staff) && c.course_staff.length) {
    lines.push("", "## Course staff", "");
    for (const s of c.course_staff) {
      lines.push(`- ${[s.name, s.role, s.email].filter(Boolean).join(" — ")}`);
    }
  }

  if (c.policies_and_procedures) {
    lines.push("", "## Policies and procedures", "", htmlToMarkdown(String(c.policies_and_procedures)));
  }

  lines.push(
    "", "---", "",
    `*Generated ${new Date().toLocaleDateString("en-AU")} from the [JacSON Course Profile Viewer](${BASE_URL}/).*`
  );
  return lines.join("\n");
}

function downloadCourseMarkdown(c) {
  downloadBlob(buildCourseMarkdown(c), safeFilename(c, "md"), "text/markdown;charset=utf-8");
}

function downloadCourseJson(c) {
  downloadBlob(JSON.stringify(c, null, 2), safeFilename(c, "json"), "application/json;charset=utf-8");
}

// ============================================================================
// Page: BROWSER (index.html)
// ============================================================================
async function initBrowser() {
  const $body  = document.getElementById("courses-body");
  const $count = document.getElementById("course-count");
  const $meta  = document.getElementById("meta-info");

  try {
    const index = await loadIndex();
    const courses = getAllCourses(index);
    STORE.allCourses = courses;

    $meta.innerHTML =
      `<span>Index generated</span> <b>${escapeHtml(fmtDate(index.generated_at))}</b>` +
      ` <span>· ${index.total_courses} profiles</span>`;

    // Populate filter dropdowns
    populateSelect("filter-level",    uniqueSorted(courses.map(c => c.study_level)));
    populateSelect("filter-mode",     uniqueSorted(courses.map(c => c.attendance)));
    populateSelect("filter-location", uniqueSorted(courses.map(c => c.location)));
    populateSelect("filter-semester", uniqueSorted(courses.map(c => c.semester_code)).reverse());

    STORE.sort = { key: "course_code", dir: "asc" };
    bindControls();
    render();
    initTheme();
  } catch (err) {
    $body.innerHTML = `<tr><td colspan="7" class="error">Error loading data: ${escapeHtml(err.message)}</td></tr>`;
    console.error(err);
  }
}

function populateSelect(id, options) {
  const $sel = document.getElementById(id);
  if (!$sel) return;
  for (const opt of options) {
    const el = document.createElement("option");
    if (typeof opt === "string") { el.value = opt; el.textContent = opt; }
    else { el.value = opt.value; el.textContent = opt.label; }
    $sel.appendChild(el);
  }
}

function bindControls() {
  for (const id of ["search", "filter-level", "filter-mode", "filter-location", "filter-semester"]) {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", render);
  }
  const $unique = document.getElementById("filter-unique");
  if ($unique) $unique.addEventListener("change", render);
  document.querySelectorAll("table.courses th[data-sort]").forEach(th => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      STORE.sort = STORE.sort.key === key
        ? { key, dir: STORE.sort.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "asc" };
      render();
    });
  });

  const $csv  = document.getElementById("export-csv");
  if ($csv)  $csv.addEventListener("click", exportFilteredAsCsv);
  const $zip  = document.getElementById("export-zip-json");
  if ($zip)  $zip.addEventListener("click", () => exportFilteredAsZip("json"));
}

async function exportFilteredAsZip(format) {
  if (typeof JSZip === "undefined") {
    alert("ZIP library (JSZip) didn't load. Please check your network connection and try again.");
    return;
  }
  const uniqueOnly = document.getElementById("filter-unique")?.checked || false;
  let filtered = applyFilters(STORE.allCourses || []);
  if (uniqueOnly) filtered = applyUniqueFilter(filtered);
  const courses = applySort(filtered);
  if (!courses.length) { alert("No courses match the current filters."); return; }
  if (courses.length > 300) {
    if (!confirm(`You're about to download ${courses.length} profiles. This may take a while. Continue?`)) return;
  }

  const $status = document.getElementById("bulk-status");
  const setStatus = msg => { if ($status) $status.textContent = msg; };
  setStatus(`Preparing ${courses.length} profile${courses.length === 1 ? "" : "s"}…`);

  const zip = new JSZip();
  const CONCURRENCY = 6;
  let done = 0, failed = 0, idx = 0;

  async function worker() {
    while (idx < courses.length) {
      const i = idx++;
      const c = courses[i];
      try {
        const full = await loadCourseJson(c.json_path);
        zip.file(safeFilename(full, "json"), JSON.stringify(full, null, 2));
      } catch (err) {
        failed++;
        console.error(`Failed to fetch ${c.json_path}:`, err);
      }
      done++;
      if (done % 10 === 0 || done === courses.length) {
        setStatus(`Building ZIP · ${done}/${courses.length}${failed ? ` (${failed} failed)` : ""}`);
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(CONCURRENCY, courses.length) }, worker));

  zip.file("README.md", [
    `# JacSON Course Profile Viewer — bulk export`,
    ``,
    `- Courses: ${courses.length - failed}${failed ? ` (${failed} failed)` : ""}`,
    `- Generated: ${new Date().toISOString()}`,
    ``,
  ].join("\n"));

  setStatus("Compressing ZIP…");
  const blob = await zip.generateAsync({ type: "blob", compression: "DEFLATE", compressionOptions: { level: 6 } });
  const stamp = new Date().toISOString().slice(0, 10);
  downloadBlob(blob, `jacson-courses-${stamp}-${courses.length}.zip`, "application/zip");
  setStatus(`Done — ${courses.length - failed} profile${courses.length - failed === 1 ? "" : "s"} exported${failed ? `, ${failed} failed` : ""}.`);
  setTimeout(() => setStatus(""), 8000);
}

function exportFilteredAsCsv() {
  const uniqueOnly = document.getElementById("filter-unique")?.checked || false;
  let filtered = applyFilters(STORE.allCourses || []);
  if (uniqueOnly) filtered = applyUniqueFilter(filtered);
  const courses = applySort(filtered);
  const columns = [
    "course_code", "course_title", "full_course_code", "study_level",
    "units", "attendance", "location", "study_period",
    "coordinating_unit", "assessments_count", "learning_outcomes_count",
    "group_assessment", "hurdle", "course_coordinator_name", "scraped_at", "url",
  ];
  const esc = v => {
    if (v == null) return "";
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [columns.join(",")];
  for (const c of courses) {
    lines.push(columns.map(col => esc(c[col])).join(","));
  }
  const now = new Date().toISOString().slice(0, 10);
  downloadBlob(lines.join("\n"), `jacson-courses-${now}-${courses.length}.csv`, "text/csv;charset=utf-8");
}

function applyUniqueFilter(courses) {
  // Keep only the most recent profile per course_code (highest semester_code wins).
  const best = new Map();
  for (const c of courses) {
    const key = c.course_code;
    if (!key) continue;
    const prev = best.get(key);
    if (!prev || Number(c.semester_code) > Number(prev.semester_code)) {
      best.set(key, c);
    }
  }
  return courses.filter(c => best.get(c.course_code) === c);
}

function applyFilters(courses) {
  const q   = (document.getElementById("search")?.value || "").trim().toLowerCase();
  const level = document.getElementById("filter-level")?.value    || "";
  const mode  = document.getElementById("filter-mode")?.value     || "";
  const loc   = document.getElementById("filter-location")?.value || "";
  const sem   = document.getElementById("filter-semester")?.value || "";

  return courses.filter(c => {
    if (q) {
      const hay = `${c.course_code} ${c.course_title || ""}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (level && c.study_level      !== level) return false;
    if (mode  && c.attendance       !== mode)  return false;
    if (loc   && c.location         !== loc)   return false;
    if (sem   && c.semester_code    !== sem)   return false;
    return true;
  });
}

function applySort(courses) {
  const { key, dir } = STORE.sort;
  const mult = dir === "asc" ? 1 : -1;
  return [...courses].sort((a, b) => {
    const av = a[key], bv = b[key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === "number" && typeof bv === "number") return (av - bv) * mult;
    return String(av).localeCompare(String(bv), "en", { numeric: true }) * mult;
  });
}

function render() {
  const $body  = document.getElementById("courses-body");
  const $count = document.getElementById("course-count");
  const uniqueOnly = document.getElementById("filter-unique")?.checked || false;
  let courses = applyFilters(STORE.allCourses || []);
  if (uniqueOnly) courses = applyUniqueFilter(courses);
  courses = applySort(courses);
  $count.textContent = courses.length;

  if (!courses.length) {
    $body.innerHTML = `<tr><td colspan="8" class="empty">No courses match the current filters.</td></tr>`;
    updateSortIndicators();
    return;
  }

  const rows = courses.map(c => {
    const pfx     = coursePrefix(c.course_code);
    const codeCls = pfx ? `code prefix-${pfx}` : "code";
    const lvlCls  = (c.study_level || "").toLowerCase().includes("post") ? "level-pill pg" : "level-pill";
    return `
      <tr>
        <td class="${codeCls}"><a href="course.html?file=${encodeURIComponent(c.json_path)}">${escapeHtml(c.course_code || "")}</a></td>
        <td>${escapeHtml(c.course_title || "")}</td>
        <td class="nowrap small">${escapeHtml(c.study_period || "")}</td>
        <td class="small">${escapeHtml(c.course_coordinator_name || "")}</td>
        <td><span class="${lvlCls}">${escapeHtml(c.study_level || "")}</span></td>
        <td>${escapeHtml(c.units || "")}</td>
        <td>${escapeHtml(c.attendance || "")}</td>
        <td>${escapeHtml(c.location || "")}</td>
      </tr>`;
  }).join("");

  $body.innerHTML = rows;
  updateSortIndicators();
}

function updateSortIndicators() {
  document.querySelectorAll("table.courses th[data-sort]").forEach(th => {
    th.classList.remove("sort-asc", "sort-desc");
    if (th.dataset.sort === STORE.sort.key) {
      th.classList.add(STORE.sort.dir === "asc" ? "sort-asc" : "sort-desc");
    }
  });
}

// ============================================================================
// Page: COURSE DETAIL (course.html)
// ============================================================================
async function initCourseDetail() {
  const $root    = document.getElementById("course-root");
  const filePath = getQueryParam("file");

  if (!filePath) {
    $root.innerHTML = `<div class="error">No course specified. Append <code>?file=profiles/{semester}/{course}.json</code> to the URL.</div>`;
    return;
  }

  try {
    const course = await loadCourseJson(filePath);
    STORE.currentCourse = course;
    renderCourseDetail($root, course);
    document.title = `${course.course_code} — ${course.course_title || "JacSON"}`;

    const $md   = document.getElementById("dl-md");
    const $json = document.getElementById("dl-json");
    if ($md)   $md.addEventListener("click",   () => downloadCourseMarkdown(course));
    if ($json) $json.addEventListener("click", () => downloadCourseJson(course));
    initTheme();
  } catch (err) {
    $root.innerHTML = `<div class="error">Error loading profile: ${escapeHtml(err.message)}</div>`;
    console.error(err);
  }
}

function renderCourseDetail($root, c) {
  const parts = [];

  // Header card
  const filePath   = getQueryParam("file");
  const rawJsonLink = filePath
    ? `<a href="${BASE_URL}/${escapeHtml(filePath)}" target="_blank" rel="noopener">Raw JSON ↗</a>`
    : "";
  const profileLink = c.url
    ? `<a href="${escapeHtml(c.url)}" target="_blank" rel="noopener">View on course-profiles.uq.edu.au ↗</a>`
    : "";

  parts.push(`
    <div class="course-header">
      <div><span class="code">${escapeHtml(c.full_course_code || c.course_code)}</span></div>
      <h1>${escapeHtml(c.course_code || "")} — ${escapeHtml(c.course_title || "")}</h1>
      <div class="meta">
        ${escapeHtml(c.study_level || "")} · ${escapeHtml(c.units || "")} units ·
        ${escapeHtml(c.attendance_mode || "")} · ${escapeHtml(c.location || "")}
        ${profileLink ? ` · ${profileLink}` : ""}
        ${rawJsonLink ? ` · ${rawJsonLink}` : ""}
      </div>
      <div class="meta small" style="margin-top:4px">Last scraped: ${escapeHtml(fmtDate(c.scraped_at))}</div>
    </div>
  `);

  // Download bar
  parts.push(`
    <div class="download-bar">
      <button id="dl-md" class="dl-btn" type="button" title="Download a Markdown version — good for LLMs and notes">
        📝 Download Markdown
      </button>
      <button id="dl-json" class="dl-btn" type="button" title="Download the raw profile JSON">
        { } Download JSON
      </button>
    </div>
  `);

  // Overview
  const overviewRows = [
    ["Study period",          c.study_period],
    ["Coordinating unit",     c.coordinating_unit],
    ["Administrative campus", c.administrative_campus],
  ].filter(([, v]) => v);
  if (overviewRows.length) {
    parts.push(`
      <div class="card">
        <h2 style="margin-top:0">Overview</h2>
        <dl class="kv-grid">
          ${overviewRows.map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd>`).join("")}
        </dl>
      </div>
    `);
  }

  // Description
  if (c.course_description) {
    parts.push(`<div class="card"><h2>Course description</h2><div>${renderLongText(c.course_description)}</div></div>`);
  }

  // Requirements
  if (c.requirements && typeof c.requirements === "object") {
    const reqRows = [];
    for (const [key, label] of [
      ["prerequisites",     "Prerequisites"],
      ["incompatible",      "Incompatible courses"],
      ["companions",        "Companions"],
      ["restrictions",      "Restrictions"],
      ["assumed_background","Assumed background"],
    ]) {
      const v = c.requirements[key];
      if (!v) continue;
      if (Array.isArray(v) && v.length) {
        reqRows.push(`<dt>${escapeHtml(label)}</dt><dd>${v.map(x => escapeHtml(String(x))).join("<br>")}</dd>`);
      } else if (typeof v === "string" && v.trim()) {
        reqRows.push(`<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(v)}</dd>`);
      }
    }
    if (reqRows.length) {
      parts.push(`<div class="card"><h2>Requirements</h2><dl class="kv-grid">${reqRows.join("")}</dl></div>`);
    }
  }

  // Aims
  if (c.course_aims) {
    parts.push(`<div class="card"><h2>Course aims</h2><div>${renderLongText(c.course_aims)}</div></div>`);
  }

  // Learning outcomes — jacson.py: [{number, description}]
  if (Array.isArray(c.learning_outcomes) && c.learning_outcomes.length) {
    parts.push(`
      <div class="card">
        <h2>Learning outcomes</h2>
        ${c.learning_outcomes.map(lo => `
          <div class="lo-item">
            <div class="lo-code">${escapeHtml(lo.number || "")}</div>
            <div>${escapeHtml(lo.description || "")}</div>
          </div>
        `).join("")}
      </div>
    `);
  }

  // Assessment summary — jacson.py key: "assessments"
  if (Array.isArray(c.assessments) && c.assessments.length) {
    const rows = c.assessments.map(a => `
      <tr>
        <td><b>${escapeHtml(a.assessment_title || "")}</b>
          ${Array.isArray(a.special_indicators) && a.special_indicators.length
            ? `<span class="small muted" style="display:block;margin-top:4px">${a.special_indicators.map(x => escapeHtml(indicatorText(x))).join(" · ")}</span>`
            : ""}
        </td>
        <td class="nowrap">${escapeHtml(a.category || "")}</td>
        <td class="weight nowrap">${escapeHtml(a.weighting || "")}</td>
        <td>${escapeHtml(a.due_date || "")}</td>
      </tr>
    `).join("");
    parts.push(`
      <div class="card">
        <h2>Assessment</h2>
        <table class="assessment">
          <thead><tr><th>Task</th><th>Category</th><th>Weight</th><th>Due</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `);
  }

  // Assessment details — jacson.py key: "assessment_details"
  if (Array.isArray(c.assessment_details) && c.assessment_details.length) {
    parts.push(`
      <div class="card">
        <h2>Assessment details</h2>
        ${c.assessment_details.map(renderAssessmentDetail).join("")}
      </div>
    `);
  }

  // Timetable
  if (c.timetable) {
    parts.push(`<div class="card"><h2>Timetable</h2><div>${renderLongText(c.timetable)}</div></div>`);
  }

  // Contacts
  if (Array.isArray(c.course_contacts) && c.course_contacts.length) {
    parts.push(`
      <div class="card">
        <h2>Course contacts</h2>
        <div class="staff-list">${c.course_contacts.map(renderStaffCard).join("")}</div>
      </div>
    `);
  }

  // Staff
  if (Array.isArray(c.course_staff) && c.course_staff.length) {
    parts.push(`
      <div class="card">
        <h2>Course staff</h2>
        <div class="staff-list">${c.course_staff.map(renderStaffCard).join("")}</div>
      </div>
    `);
  }

  // Learning activities
  if (Array.isArray(c.learning_activities) && c.learning_activities.length) {
    const rows = c.learning_activities.map(la => {
      const topic = stripLoSuffix(htmlToText(la.topic || ""));
      const los   = Array.isArray(la.learning_outcomes)
                      ? la.learning_outcomes.join(", ")
                      : (la.learning_outcomes || "");
      return `<tr>
        <td class="nowrap">${escapeHtml(la.learning_period || "")}</td>
        <td class="nowrap">${escapeHtml(la.activity_type  || "")}</td>
        <td>${escapeHtml(topic)}</td>
        <td class="nowrap small">${escapeHtml(los)}</td>
      </tr>`;
    }).join("");
    parts.push(`
      <div class="card">
        <h2>Learning activities</h2>
        <table class="assessment">
          <thead><tr><th>Period</th><th>Type</th><th>Topic</th><th>LOs</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `);
  }

  // Learning resources
  if (c.learning_resources && typeof c.learning_resources === "object") {
    const lrRows = [];
    for (const [k, val] of Object.entries(c.learning_resources)) {
      if (!val) continue;
      const label = k.replace(/_/g, " ").replace(/\b\w/g, s => s.toUpperCase());
      const rendered = Array.isArray(val)
        ? val.map(v => escapeHtml(String(v))).join("<br>")
        : renderLongText(String(val));
      lrRows.push(`<dt>${escapeHtml(label)}</dt><dd>${rendered}</dd>`);
    }
    if (lrRows.length) {
      parts.push(`<div class="card"><h2>Learning resources</h2><dl class="kv-grid">${lrRows.join("")}</dl></div>`);
    }
  } else if (typeof c.learning_resources === "string" && c.learning_resources.trim()) {
    parts.push(`<div class="card"><h2>Learning resources</h2><div>${renderLongText(c.learning_resources)}</div></div>`);
  }

  // Policies
  if (c.policies_and_procedures) {
    parts.push(`<div class="card"><h2>Policies and procedures</h2><div>${renderLongText(c.policies_and_procedures)}</div></div>`);
  }

  $root.innerHTML = parts.join("");
}

// Render one assessment detail block — jacson.py field names
function renderAssessmentDetail(a) {
  const meta = [];
  if (a.weighting)        meta.push(`<b>Weight:</b> ${escapeHtml(a.weighting)}`);
  if (a.due_date)         meta.push(`<b>Due:</b> ${escapeHtml(a.due_date)}`);
  if (a.category)         meta.push(`<b>Category:</b> ${escapeHtml(a.category)}`);
  if (a.mode)             meta.push(`<b>Mode:</b> ${escapeHtml(a.mode)}`);
  if (a.other_conditions) meta.push(`<b>Conditions:</b> ${escapeHtml(a.other_conditions)}`);

  // learning_objectives is a string like "LO1, LO2" in jacson.py
  const loStr = a.learning_objectives ? String(a.learning_objectives) : "";

  // special_indicators: [{special_indicators_class, special_indicator_text}]
  let indicators = "";
  if (Array.isArray(a.special_indicators) && a.special_indicators.length) {
    indicators = a.special_indicators
      .map(s => `<span class="chip">${escapeHtml(indicatorText(s))}</span>`)
      .join(" ");
  }

  const sections = [];
  for (const [key, label] of [
    ["task_description",    "Task description"],
    ["submission_guidelines","Submission guidelines"],
    ["deferral_or_extension","Deferral or extension"],
    ["late_submission",     "Late submission"],
    ["ai_statement",        "AI / academic integrity"],
  ]) {
    const v = a[key];
    if (!v) continue;
    sections.push(`<h4>${label}</h4>${renderLongText(String(v))}`);
  }

  return `
    <div class="assessment-detail">
      <h4>${escapeHtml(a.assessment_title || "Assessment")}</h4>
      ${meta.length ? `<div class="a-meta">${meta.join(" · ")}</div>` : ""}
      ${indicators ? `<div style="margin-bottom:8px">${indicators}</div>` : ""}
      ${loStr ? `<div class="small muted" style="margin-bottom:8px">Linked LOs: ${escapeHtml(loStr)}</div>` : ""}
      ${sections.join("")}
    </div>
  `;
}

function renderStaffCard(s) {
  return `
    <div class="staff-card">
      <div class="name">${escapeHtml(s.name || "")}</div>
      ${s.role  ? `<div class="role">${escapeHtml(s.role)}</div>`  : ""}
      ${s.email ? `<div class="email"><a href="mailto:${escapeHtml(s.email)}">${escapeHtml(s.email)}</a></div>` : ""}
    </div>
  `;
}

function renderLongText(text) {
  if (!text) return "";
  const paras = String(text).split(/\n{2,}/).map(p => p.trim()).filter(Boolean);
  return paras.map(p => `<p>${escapeHtml(p).replace(/\n/g, "<br>")}</p>`).join("");
}

// ============================================================================
// Theme toggle (Classic ⇄ Fun), shared across all pages
// ============================================================================
const THEMES       = ["classic", "fun"];
const THEME_LABELS = { classic: "Classic", fun: "Fun" };
const THEME_ICONS  = { classic: "◐", fun: "✦" };
const THEME_KEY    = "jacson-theme";

function getCurrentTheme() {
  const t = document.documentElement.getAttribute("data-theme");
  return THEMES.includes(t) ? t : "classic";
}

function applyTheme(theme) {
  if (!THEMES.includes(theme)) theme = "classic";
  document.documentElement.setAttribute("data-theme", theme);
  try { localStorage.setItem(THEME_KEY, theme); } catch (_) {}
  updateThemeToggleLabel(theme);
}

function updateThemeToggleLabel(theme) {
  const $btn = document.getElementById("theme-toggle");
  if (!$btn) return;
  const next   = theme === "classic" ? "fun" : "classic";
  const $label = $btn.querySelector(".tt-label");
  const $icon  = $btn.querySelector(".tt-icon");
  if ($label) $label.textContent = THEME_LABELS[next];
  if ($icon)  $icon.textContent  = THEME_ICONS[next];
  $btn.setAttribute("aria-pressed", theme === "fun" ? "true" : "false");
  $btn.title = `Switch to ${THEME_LABELS[next]} theme`;
}

function initTheme() {
  const current = getCurrentTheme();
  updateThemeToggleLabel(current);
  const $btn = document.getElementById("theme-toggle");
  if ($btn && !$btn.dataset.themeBound) {
    $btn.dataset.themeBound = "1";
    $btn.addEventListener("click", () => {
      applyTheme(getCurrentTheme() === "classic" ? "fun" : "classic");
    });
  }
}

if (typeof document !== "undefined") initTheme();

// Export to window so inline <script> tags can call them
window.JacSON = { initBrowser, initCourseDetail, initTheme, applyTheme };
