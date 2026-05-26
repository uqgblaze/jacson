/**
 * jacdash.js — JacDash SPA logic
 *
 * Responsibilities:
 *   - Poll /api/dashboard every 5 s to keep sidebar data fresh
 *   - Start manual runs via /api/run
 *   - Poll /api/log while a job is running (live terminal output)
 *   - Schedule modal: GET + POST /api/schedule
 *   - Users modal:    GET / POST / DELETE /api/users
 */

"use strict";

/* ── State ──────────────────────────────────────────────────── */

let _currentJobId   = null;   // job being polled
let _logOffset      = 0;      // byte offset for log polling
let _logPollTimer   = null;   // setInterval handle
let _dashPollTimer  = null;   // setInterval handle
let _isRunning      = false;  // local mirror of job state

/* ── Boot ───────────────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
  refreshDashboard();
  _dashPollTimer = setInterval(refreshDashboard, 5000);
});

/* ── Dashboard poll ─────────────────────────────────────────── */

async function refreshDashboard() {
  try {
    const data = await apiFetch("/api/dashboard");
    applyDashboard(data);
  } catch (e) {
    console.warn("Dashboard poll failed:", e);
  }
}

function applyDashboard(data) {
  setText("server-time",   data.server_time ?? "—");
  setText("courses-count", data.courses_count != null
    ? data.courses_count.toLocaleString() : "—");

  const nextRun = formatDatetime(data.next_run_at);
  setText("next-run",  nextRun);
  setText("stat-next", nextRun);

  const s = data.job_state ?? {};

  // Status log
  setText("stat-started",  formatDatetime(s.started_at));
  setText("stat-finished", formatDatetime(s.finished_at));
  setText("stat-scraped",  s.courses_scraped != null ? s.courses_scraped : "—");
  setText("stat-skipped",  s.courses_skipped != null ? s.courses_skipped : "—");

  const statusEl = document.getElementById("stat-status");
  if (statusEl) {
    statusEl.textContent = s.status ?? "—";
    statusEl.className = "jd-status-val";
    if (s.status === "success") statusEl.classList.add("jd-status-val--success");
    if (s.status === "failed")  statusEl.classList.add("jd-status-val--failed");
  }

  // Sync running state
  const nowRunning = s.status === "running";

  if (nowRunning && !_isRunning) {
    // Another session started a job (e.g. scheduled run)
    _enterRunningState(s.current_job_id, false);
  } else if (!nowRunning && _isRunning && !_logPollTimer) {
    // Job finished externally
    _exitRunningState(s.status === "success");
  }

  // Show download button if there's a past job
  const dlBtn = document.getElementById("btn-download");
  if (dlBtn) {
    const jobId = s.current_job_id;
    dlBtn.style.display = jobId ? "inline-block" : "none";
    if (jobId) dlBtn.dataset.jobId = jobId;
  }
}

/* ── Manual run ─────────────────────────────────────────────── */

async function startRun() {
  if (_isRunning) return;

  try {
    const data = await apiFetch("/api/run", { method: "POST" });
    _enterRunningState(data.job_id, true);
  } catch (e) {
    if (e.status === 409) {
      appendLog("[JacDash] A job is already running.\n");
    } else {
      appendLog("[JacDash] Failed to start run: " + e.message + "\n");
    }
  }
}

function _enterRunningState(jobId, clearLog) {
  _isRunning    = true;
  _currentJobId = jobId;
  _logOffset    = 0;

  if (clearLog) {
    const pre = document.getElementById("log-output");
    if (pre) pre.textContent = "";
  }

  // Button UI
  const btnRun = document.getElementById("btn-run");
  if (btnRun) {
    btnRun.classList.add("jd-btn--running");
    btnRun.disabled = true;
    setText("btn-run-label", "Running. Please wait…");
  }

  // Disable other controls while running
  ["btn-schedule", "btn-sheet", "btn-users"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = true;
  });

  // Show download button
  const dlBtn = document.getElementById("btn-download");
  if (dlBtn && jobId) {
    dlBtn.style.display = "inline-block";
    dlBtn.dataset.jobId = jobId;
  }

  // Start log polling
  _logPollTimer = setInterval(() => pollLog(jobId), 1500);
}

function _exitRunningState(success) {
  _isRunning = false;

  if (_logPollTimer) {
    clearInterval(_logPollTimer);
    _logPollTimer = null;
  }

  // Restore button
  const btnRun = document.getElementById("btn-run");
  if (btnRun) {
    btnRun.classList.remove("jd-btn--running");
    btnRun.disabled = false;
    setText("btn-run-label", "Start Manual Run");
  }

  // Re-enable controls
  ["btn-schedule", "btn-sheet", "btn-users"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.disabled = false;
  });

  appendLog(success
    ? "\n[JacDash] Run completed successfully.\n"
    : "\n[JacDash] Run finished with errors. Check the log above.\n");

  // Final dashboard refresh for updated stats
  refreshDashboard();
}

/* ── Log polling ─────────────────────────────────────────────── */

async function pollLog(jobId) {
  try {
    const data = await apiFetch(
      `/api/log?job_id=${encodeURIComponent(jobId)}&offset=${_logOffset}`
    );

    if (data.lines) {
      appendLog(data.lines);
      _logOffset = data.next_offset;
    }

    if (!data.is_running) {
      // Job finished — do one final poll to capture tail
      _exitRunningState(true);
      // Refresh to get final status
      setTimeout(refreshDashboard, 500);
    }
  } catch (e) {
    console.warn("Log poll failed:", e);
  }
}

function appendLog(text) {
  const pre = document.getElementById("log-output");
  if (!pre) return;
  pre.textContent += text;
  pre.scrollTop = pre.scrollHeight;
}

function downloadLog() {
  const btn = document.getElementById("btn-download");
  if (!btn || !btn.dataset.jobId) return;
  window.location = `/api/log?job_id=${encodeURIComponent(btn.dataset.jobId)}&download=1`;
}

/* ── Schedule modal ─────────────────────────────────────────── */

async function openScheduleModal() {
  try {
    const data = await apiFetch("/api/schedule");
    // Set time input
    const timeEl = document.getElementById("schedule-time");
    if (timeEl && data.time) timeEl.value = data.time;

    // Set day checkboxes
    const selectedDays = new Set((data.days || "").split(",").map(d => d.trim()));
    document.querySelectorAll("#schedule-days input[type=checkbox]").forEach(cb => {
      cb.checked = selectedDays.has(cb.value);
    });
  } catch (e) {
    console.warn("Could not load schedule:", e);
  }

  openModal("modal-schedule");
}

async function saveSchedule() {
  const timeEl = document.getElementById("schedule-time");
  const time   = timeEl ? timeEl.value : "";

  const days = Array.from(
    document.querySelectorAll("#schedule-days input[type=checkbox]:checked")
  ).map(cb => cb.value).join(",");

  if (!time || !days) {
    alert("Please select at least one day and enter a time.");
    return;
  }

  try {
    await apiFetch("/api/schedule", {
      method: "POST",
      body: JSON.stringify({ time, days }),
    });
    closeModal("modal-schedule");
    refreshDashboard();
  } catch (e) {
    alert("Failed to save schedule: " + e.message);
  }
}

/* ── Users modal ─────────────────────────────────────────────── */

async function openUsersModal() {
  setMsg("users-msg", "");
  await loadUsers();
  openModal("modal-users");
}

async function loadUsers() {
  try {
    const users = await apiFetch("/api/users");
    renderUserList(users);
  } catch (e) {
    console.warn("Could not load users:", e);
  }
}

function renderUserList(users) {
  const list = document.getElementById("user-list");
  if (!list) return;

  if (!users || users.length === 0) {
    list.innerHTML = '<div class="jd-user-row" style="color:#999;justify-content:center">No users yet.</div>';
    return;
  }

  list.innerHTML = users.map(u => `
    <div class="jd-user-row">
      <div>
        <div class="jd-user-name">${esc(u.full_name)}</div>
        <div class="jd-user-uname">${esc(u.uq_username)}</div>
      </div>
      <button class="jd-user-remove" onclick="removeUser('${esc(u.uq_username)}')">
        Remove
      </button>
    </div>
  `).join("");
}

async function addUser() {
  const unameEl = document.getElementById("new-username");
  const nameEl  = document.getElementById("new-fullname");
  const uname   = (unameEl?.value ?? "").trim();
  const name    = (nameEl?.value  ?? "").trim();

  if (!uname || !name) {
    setMsg("users-msg", "Please enter both a UQ username and a full name.");
    return;
  }

  try {
    await apiFetch("/api/users", {
      method: "POST",
      body: JSON.stringify({ uq_username: uname, full_name: name }),
    });
    if (unameEl) unameEl.value = "";
    if (nameEl)  nameEl.value  = "";
    setMsg("users-msg", "");
    await loadUsers();
  } catch (e) {
    setMsg("users-msg", e.message || "Failed to add user.");
  }
}

async function removeUser(uname) {
  if (!confirm(`Remove ${uname} from JacDash?`)) return;
  try {
    await apiFetch(`/api/users/${encodeURIComponent(uname)}`, { method: "DELETE" });
    await loadUsers();
  } catch (e) {
    setMsg("users-msg", e.message || "Failed to remove user.");
  }
}

/* ── Modal helpers ───────────────────────────────────────────── */

function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("is-open");
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove("is-open");
}

// Close on overlay click
document.addEventListener("click", e => {
  if (e.target.classList.contains("jd-modal-overlay")) {
    e.target.classList.remove("is-open");
  }
});

/* ── Utility ─────────────────────────────────────────────────── */

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value ?? "—";
}

function setMsg(id, msg) {
  const el = document.getElementById(id);
  if (el) el.textContent = msg;
}

function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatDatetime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleString("en-AU", {
      day:    "2-digit",
      month:  "short",
      year:   "numeric",
      hour:   "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  } catch {
    return iso;
  }
}

async function apiFetch(url, options = {}) {
  const defaults = {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
  };
  const resp = await fetch(url, { ...defaults, ...options,
    headers: { ...defaults.headers, ...(options.headers ?? {}) }
  });

  if (!resp.ok) {
    let errMsg = `HTTP ${resp.status}`;
    try {
      const body = await resp.json();
      errMsg = body.error || errMsg;
    } catch { /* ignore */ }
    const err = new Error(errMsg);
    err.status = resp.status;
    throw err;
  }

  if (resp.status === 204) return null;
  return resp.json();
}
