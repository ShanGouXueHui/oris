#!/usr/bin/env python3
from pathlib import Path

path = Path('/home/admin/projects/oris/scripts/dev_employee_web_console.py')
text = path.read_text(encoding='utf-8')

text = text.replace(
    '<input id="console_token" type="password" placeholder="paste local console token" />',
    '<input id="console_token" type="password" placeholder="paste Console API token" autocomplete="off" />',
)
text = text.replace(
    '<select id="project_key"></select>',
    '<select id="project_key"><option value="">Enter a valid Console API token first</option></select>\n'
    '      <div id="project_status" class="muted">Project list loads automatically after the token changes.</div>',
)

old = '''const splitLines = (value) => value.split('\\n').map(x => x.trim()).filter(Boolean);
function consoleToken() { return document.getElementById('console_token').value.trim(); }
function rememberToken() { localStorage.setItem('oris_console_token', consoleToken()); }
async function api(path, options={}) {
  const headers = Object.assign({}, options.headers || {});
  const token = consoleToken();
  if (token) headers['X-ORIS-Console-Token'] = token;
  const resp = await fetch(path, Object.assign({}, options, {headers}));
  const data = await resp.json();
  if (!resp.ok) throw new Error(JSON.stringify(data, null, 2));
  return data;
}
async function loadProjects() {
  rememberToken();
  const data = await api('/api/projects');
  const select = document.getElementById('project_key');
  select.innerHTML = '';
  for (const key of data.projects || []) {
    const opt = document.createElement('option'); opt.value = key; opt.textContent = key; select.appendChild(opt);
  }
}
async function submitGoal() {
  rememberToken();
  const payload = {
    project_key: document.getElementById('project_key').value,
    objective: document.getElementById('objective').value.trim(),
    constraints: splitLines(document.getElementById('constraints').value),
    expected_checks: splitLines(document.getElementById('expected_checks').value),
    notes: ['Submitted through ORIS local Web console prototype.']
  };
  const taskId = document.getElementById('task_id').value.trim();
  const commitMessage = document.getElementById('commit_message').value.trim();
  if (taskId) payload.task_id = taskId;
  if (commitMessage) payload.commit_message = commitMessage;
  const data = await api('/api/goals', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
  document.getElementById('submit_result').textContent = JSON.stringify(data, null, 2);
  if (data.task_id) document.getElementById('lookup_task_id').value = data.task_id;
}
'''

new = '''const splitLines = (value) => value.split('\\n').map(x => x.trim()).filter(Boolean);
function consoleToken() { return document.getElementById('console_token').value.trim(); }
function rememberToken() { localStorage.setItem('oris_console_token', consoleToken()); }
function setProjectPlaceholder(message) {
  const select = document.getElementById('project_key');
  select.innerHTML = '';
  const opt = document.createElement('option');
  opt.value = '';
  opt.textContent = message;
  select.appendChild(opt);
}
function setProjectStatus(message) {
  document.getElementById('project_status').textContent = message;
}
function setSubmitResult(message) {
  document.getElementById('submit_result').textContent = message;
}
async function api(path, options={}) {
  const headers = Object.assign({}, options.headers || {});
  const token = consoleToken();
  if (token) headers['X-ORIS-Console-Token'] = token;
  const resp = await fetch(path, Object.assign({}, options, {headers}));
  const data = await resp.json();
  if (!resp.ok) throw new Error(JSON.stringify(data, null, 2));
  return data;
}
async function loadProjects() {
  rememberToken();
  if (!consoleToken()) {
    setProjectPlaceholder('Enter a valid Console API token first');
    setProjectStatus('Console API token is required before projects can be loaded.');
    return;
  }
  setProjectPlaceholder('Loading projects...');
  setProjectStatus('Loading allowed projects...');
  try {
    const data = await api('/api/projects');
    const projects = data.projects || [];
    const select = document.getElementById('project_key');
    select.innerHTML = '';
    if (!projects.length) {
      setProjectPlaceholder('No allowed projects returned');
      setProjectStatus('The token was accepted, but the project allowlist returned no projects.');
      return;
    }
    for (const key of projects) {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = key;
      select.appendChild(opt);
    }
    setProjectStatus(`Loaded ${projects.length} allowed project(s).`);
    setSubmitResult('Project list loaded successfully.');
  } catch (error) {
    setProjectPlaceholder('Unable to load projects');
    setProjectStatus('Project loading failed. Replace the saved token with the current Console API token.');
    setSubmitResult(`Project load failed:\n${String(error)}`);
  }
}
async function submitGoal() {
  rememberToken();
  const projectKey = document.getElementById('project_key').value;
  const objective = document.getElementById('objective').value.trim();
  if (!consoleToken()) {
    setSubmitResult('Cannot submit: Console API token is missing.');
    return;
  }
  if (!projectKey) {
    setSubmitResult('Cannot submit: no project is selected. Reload the project list with a valid token.');
    return;
  }
  if (!objective) {
    setSubmitResult('Cannot submit: objective is required.');
    return;
  }
  const payload = {
    project_key: projectKey,
    objective,
    constraints: splitLines(document.getElementById('constraints').value),
    expected_checks: splitLines(document.getElementById('expected_checks').value),
    notes: ['Submitted through ORIS public Web console.']
  };
  const taskId = document.getElementById('task_id').value.trim();
  const commitMessage = document.getElementById('commit_message').value.trim();
  if (taskId) payload.task_id = taskId;
  if (commitMessage) payload.commit_message = commitMessage;
  try {
    const data = await api('/api/goals', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
    setSubmitResult(JSON.stringify(data, null, 2));
    if (data.task_id) document.getElementById('lookup_task_id').value = data.task_id;
  } catch (error) {
    setSubmitResult(`Submit failed:\n${String(error)}`);
  }
}
'''

if old not in text:
    raise SystemExit('ERROR: expected JavaScript block not found; refusing partial patch')
text = text.replace(old, new, 1)

old_tail = '''document.getElementById('console_token').value = localStorage.getItem('oris_console_token') || '';
loadProjects().catch(e => { document.getElementById('submit_result').textContent = String(e); });'''
new_tail = '''const tokenInput = document.getElementById('console_token');
tokenInput.value = localStorage.getItem('oris_console_token') || '';
tokenInput.addEventListener('change', loadProjects);
tokenInput.addEventListener('blur', () => { if (consoleToken()) loadProjects(); });
if (consoleToken()) {
  loadProjects();
} else {
  setProjectPlaceholder('Enter a valid Console API token first');
  setProjectStatus('Paste the current Console API token; projects will then load automatically.');
}'''
if old_tail not in text:
    raise SystemExit('ERROR: expected JavaScript initialization block not found')
text = text.replace(old_tail, new_tail, 1)

path.write_text(text, encoding='utf-8')
print('PATCHED_WEB_CONSOLE_PROJECT_DROPDOWN=true')
