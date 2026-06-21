from __future__ import annotations


def page() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ORIS Dev Employee Console</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f6f7fb; color: #1f2937; }
    header { background: #111827; color: white; padding: 18px 24px; }
    main { max-width: 1180px; margin: 0 auto; padding: 24px; }
    section { background: white; border-radius: 14px; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08); padding: 20px; margin-bottom: 18px; }
    label { display: block; font-weight: 650; margin: 12px 0 6px; }
    input, select, textarea { width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 10px; font: inherit; }
    textarea { min-height: 150px; }
    button { border: 0; border-radius: 10px; padding: 10px 14px; background: #2563eb; color: white; font-weight: 700; cursor: pointer; margin-right: 8px; }
    button.secondary { background: #64748b; }
    pre { background: #0f172a; color: #d1fae5; padding: 14px; border-radius: 10px; overflow-x: auto; white-space: pre-wrap; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
    .muted { color: #64748b; font-size: 0.94rem; }
    .pill { display: inline-block; padding: 3px 8px; border-radius: 999px; background: #e0f2fe; color: #075985; font-size: 0.82rem; margin-left: 6px; }
  </style>
</head>
<body>
  <header><h1>ORIS Dev Employee Console <span class="pill">local only</span></h1></header>
  <main>
    <section>
      <h2>Submit a governed development goal</h2>
      <p class="muted">Submission is disabled unless ORIS_DEV_EMPLOYEE_WEB_CONSOLE_SUBMIT_ENABLED=1. The console forwards to the loopback intake API; it does not invoke Codex or mutate repositories directly.</p>
      <div class="grid">
        <div><label>Project</label><select id="project"></select></div>
        <div><label>Optional task id</label><input id="taskId" placeholder="goal-project-YYYYMMDD-HHMMSS" /></div>
      </div>
      <label>Objective</label><textarea id="objective" placeholder="Describe the concrete product outcome, constraints, and acceptance checks..."></textarea>
      <label>Constraints, one per line</label><textarea id="constraints" placeholder="No production changes&#10;Preserve existing tests"></textarea>
      <label>Expected checks, one per line</label><textarea id="checks" placeholder="pytest&#10;python -m compileall"></textarea>
      <label>Commit message</label><input id="commitMessage" placeholder="feat: implement ..." />
      <label>Console token</label><input id="consoleToken" type="password" placeholder="X-ORIS-Console-Token" />
      <button onclick="submitGoal()">Submit goal</button>
      <button class="secondary" onclick="refreshGoals()">Refresh goals</button>
    </section>
    <section><h2>Goals</h2><div id="goals"></div></section>
    <section><h2>Status / evidence</h2><pre id="output">Ready.</pre></section>
  </main>
<script>
function lines(id) { return document.getElementById(id).value.split('\n').map(x => x.trim()).filter(Boolean); }
function show(x) { document.getElementById('output').textContent = typeof x === 'string' ? x : JSON.stringify(x, null, 2); }
async function api(path, opts={}) { const resp = await fetch(path, opts); const text = await resp.text(); try { return {status: resp.status, body: JSON.parse(text)}; } catch { return {status: resp.status, body: text}; } }
async function loadProjects() { const r = await api('/api/projects'); const select = document.getElementById('project'); select.innerHTML = ''; for (const project of ((r.body && r.body.projects) || [])) { const option = document.createElement('option'); option.value = project; option.textContent = project; select.appendChild(option); } }
async function refreshGoals() { const r = await api('/api/goals'); const div = document.getElementById('goals'); const items = (r.body && r.body.items) || []; div.innerHTML = items.map(item => `<p><button class="secondary" onclick="status('${item.task_id}')">status</button><b>${item.task_id}</b> ${item.status || ''} ${item.terminal ? '(terminal)' : ''}</p>`).join('') || '<p class="muted">No goals yet.</p>'; show(r.body); }
async function status(taskId) { const r = await api('/api/goals/' + encodeURIComponent(taskId)); show(r.body); }
async function submitGoal() { const token = document.getElementById('consoleToken').value; const payload = { project_key: document.getElementById('project').value, task_id: document.getElementById('taskId').value || undefined, objective: document.getElementById('objective').value, constraints: lines('constraints'), expected_checks: lines('checks'), commit_message: document.getElementById('commitMessage').value || undefined }; const r = await api('/api/goals', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-ORIS-Console-Token': token}, body: JSON.stringify(payload)}); show(r.body); await refreshGoals(); }
loadProjects().then(refreshGoals).catch(err => show(String(err)));
</script>
</body>
</html>
"""
