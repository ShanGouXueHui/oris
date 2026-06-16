#!/usr/bin/env bash

ORIS="/home/admin/projects/oris"
PRODUCT="/home/admin/projects/oris-final-acceptance-api"
TASK_ID="fix-conversational-intent-boundaries-20260617"
STAMP="$(date +%Y%m%d%H%M%S)"
SOURCE="scripts/dev_employee_openclaw_provider.py"
TEST_FILE="tests/test_dev_employee_openclaw_provider.py"
LOG_DIR="$ORIS/logs/dev_employee/conversational_web"
RUN_LOG="$LOG_DIR/fix-intent-boundaries-$STAMP.log"
EVIDENCE_JSON="$LOG_DIR/fix-intent-boundaries-$STAMP.json"

RESULT="FAILED"
PATCH_RESULT="NOT_RUN"
STATIC_CHECKS="NOT_RUN"
TEST_RESULT="NOT_RUN"
REGRESSION_MESSAGE="NOT_RUN"
CONTROL_COMMANDS="NOT_RUN"
NEGATED_SECRET_POLICY="NOT_RUN"
SERVICE_RESTART="NOT_RUN"
WEB_HEALTH="NOT_RUN"
ACTIVE_QUEUE_GATE="NOT_RUN"
PRODUCT_SHA_UNCHANGED="NOT_VERIFIED"
PRODUCT_WORKTREE_CLEAN="NOT_VERIFIED"
CODE_COMMIT=""
LOG_COMMIT=""
FAILURE_CODE=""
NEXT_ACTION="INSPECT_INTENT_BOUNDARY_REPAIR"

mkdir -p "$LOG_DIR"
: > "$RUN_LOG"

service_state() { systemctl --user is-active "$1" 2>/dev/null || true; }

write_evidence() {
  python3 - "$EVIDENCE_JSON" <<PY
import json
payload={
  "task_id":"$TASK_ID",
  "checked_at":"$(date -Is)",
  "result":"$RESULT",
  "failure_code":"$FAILURE_CODE" or None,
  "patch_result":"$PATCH_RESULT",
  "static_checks":"$STATIC_CHECKS",
  "test_result":"$TEST_RESULT",
  "regression_message":"$REGRESSION_MESSAGE",
  "control_commands":"$CONTROL_COMMANDS",
  "negated_secret_policy":"$NEGATED_SECRET_POLICY",
  "service_restart":"$SERVICE_RESTART",
  "web_health":"$WEB_HEALTH",
  "active_queue_gate":"$ACTIVE_QUEUE_GATE",
  "product_sha_unchanged":"$PRODUCT_SHA_UNCHANGED",
  "product_worktree_clean":"$PRODUCT_WORKTREE_CLEAN",
  "code_commit":"$CODE_COMMIT" or None,
  "services":{
    "openclaw":"$(service_state openclaw-gateway.service)",
    "bridge":"$(service_state oris-dev-employee-bridge.service)",
    "intake":"$(service_state oris-dev-employee-intake.service)",
    "web":"$(service_state oris-dev-employee-web-console.service)"
  },
  "real_product_task_submitted":False,
  "real_product_change":False,
  "next_action":"$NEXT_ACTION"
}
open("$EVIDENCE_JSON","w",encoding="utf-8").write(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
PY
}

commit_log() {
  git add -- "${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}" >> "$RUN_LOG" 2>&1 || return 1
  git commit --only -m "test(dev-employee): verify intent boundary repair $STAMP" -- "${RUN_LOG#$ORIS/}" "${EVIDENCE_JSON#$ORIS/}" >> "$RUN_LOG" 2>&1 || return 1
  git push origin main >> "$RUN_LOG" 2>&1 || return 1
  LOG_COMMIT="$(git rev-parse HEAD 2>/dev/null || true)"
}

summary() {
  echo
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "PATCH_RESULT=$PATCH_RESULT"
  echo "STATIC_CHECKS=$STATIC_CHECKS"
  echo "TEST_RESULT=$TEST_RESULT"
  echo "REGRESSION_MESSAGE=$REGRESSION_MESSAGE"
  echo "CONTROL_COMMANDS=$CONTROL_COMMANDS"
  echo "NEGATED_SECRET_POLICY=$NEGATED_SECRET_POLICY"
  echo "ACTIVE_QUEUE_GATE=$ACTIVE_QUEUE_GATE"
  echo "SERVICE_RESTART=$SERVICE_RESTART"
  echo "WEB_HEALTH=$WEB_HEALTH"
  echo "PRODUCT_SHA_UNCHANGED=$PRODUCT_SHA_UNCHANGED"
  echo "PRODUCT_WORKTREE_CLEAN=$PRODUCT_WORKTREE_CLEAN"
  echo "CODE_COMMIT=$CODE_COMMIT"
  echo "LOG_COMMIT=$LOG_COMMIT"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "OPENCLAW_SERVICE=$(service_state openclaw-gateway.service)"
  echo "BRIDGE_SERVICE=$(service_state oris-dev-employee-bridge.service)"
  echo "INTAKE_SERVICE=$(service_state oris-dev-employee-intake.service)"
  echo "WEB_CONSOLE_SERVICE=$(service_state oris-dev-employee-web-console.service)"
  echo "REAL_PRODUCT_TASK_SUBMITTED=NO"
  echo "REAL_PRODUCT_CHANGE=NO"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  write_evidence
  commit_log || true
  summary
  exit 1
}

[ "$(id -un)" = "admin" ] || { FAILURE_CODE="wrong_linux_user"; NEXT_ACTION="RUN_AS_ADMIN"; write_evidence; summary; exit 1; }
cd "$ORIS" || { FAILURE_CODE="oris_directory_missing"; NEXT_ACTION="RESTORE_ORIS_REPOSITORY"; write_evidence; summary; exit 1; }

[ -z "$(git status --porcelain --untracked-files=no)" ] || fail "oris_tracked_worktree_dirty" "INSPECT_ORIS_GIT_STATE"
git fetch origin main >> "$RUN_LOG" 2>&1 || fail "oris_fetch_failed" "RESOLVE_ORIS_GIT_FETCH"
git restore --source=origin/main --staged --worktree -- . >> "$RUN_LOG" 2>&1 || fail "tracked_worktree_sync_failed" "INSPECT_ORIS_GIT_STATE"
git reset --mixed origin/main >> "$RUN_LOG" 2>&1 || fail "local_branch_sync_failed" "INSPECT_ORIS_GIT_STATE"

BASE_PRODUCT_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
BASE_PRODUCT_REMOTE="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n1)"
[ -n "$BASE_PRODUCT_SHA" ] && [ "$BASE_PRODUCT_SHA" = "$BASE_PRODUCT_REMOTE" ] || fail "product_baseline_mismatch" "INSPECT_PRODUCT_REPOSITORY"
[ -z "$(git -C "$PRODUCT" status --porcelain --untracked-files=no)" ] || fail "product_baseline_dirty" "INSPECT_PRODUCT_REPOSITORY"

ACTIVE_COUNT="$(find orchestration/dev_employee_queue -maxdepth 1 -type f \( -name '*.queued.json' -o -name '*.running.json' \) 2>/dev/null | wc -l | tr -d ' ')"
[ "$ACTIVE_COUNT" = "0" ] || fail "active_queue_not_empty" "INSPECT_ACTIVE_TASKS"
ACTIVE_QUEUE_GATE="PASS"

python3 - "$SOURCE" "$TEST_FILE" <<'PY' >> "$RUN_LOG" 2>&1
from pathlib import Path
import sys

source_path=Path(sys.argv[1])
test_path=Path(sys.argv[2])
source=source_path.read_text(encoding='utf-8')
tests=test_path.read_text(encoding='utf-8')

old_prompt='''        "Set requires_confirmation=true for production changes, destructive/irreversible operations, secret handling, billing, or purchases.\\n"\n        "For create_task, preserve the user's real objective and select exactly one available project.\\n"'''
new_prompt='''        "Set requires_confirmation=true for production changes, destructive/irreversible operations, secret handling, billing, or purchases.\\n"\n        "A negative safety constraint such as do not read or modify secrets is not a secret operation and must not require confirmation.\\n"\n        "For create_task, preserve the user's real objective and select exactly one available project.\\n"'''
if source.count(old_prompt) != 1:
    raise SystemExit('router prompt anchor mismatch')
source=source.replace(old_prompt,new_prompt,1)

old_constants='''    STATUS_WORDS = ("进度", "状态", "怎么样了", "完成了吗", "status", "progress", "how is")\n    CANCEL_WORDS = ("停止任务", "取消任务", "停掉", "停止", "取消", "stop task", "cancel task")\n    RETRY_WORDS = ("重试", "再试一次", "重新执行", "retry", "try again")\n    HELP_WORDS = ("帮助", "怎么用", "help", "what can you do")\n'''
new_constants='''    CONTROL_PHRASES = {\n        "status": {\n            "进度", "查看进度", "任务进度", "查看任务进度",\n            "状态", "查看状态", "任务状态", "查看任务状态",\n            "怎么样了", "现在怎么样了", "完成了吗", "任务完成了吗",\n            "status", "checkstatus", "progress", "showprogress", "howisitgoing",\n        },\n        "cancel": {\n            "停止任务", "取消任务", "停止当前任务", "取消当前任务", "停掉任务",\n            "stop", "stoptask", "cancel", "canceltask",\n        },\n        "retry": {\n            "重试", "重试任务", "重新执行", "重新执行任务", "再试一次",\n            "retry", "tryagain",\n        },\n        "help": {\n            "帮助", "怎么用", "如何使用", "你能做什么",\n            "help", "whatcanyoudo",\n        },\n    }\n\n    @classmethod\n    def control_intent(cls, text: str) -> str | None:\n        normalized = re.sub(r"[\\s，。！？!?；;：:、]+", "", text.strip().lower())\n        for prefix in ("麻烦帮我", "请帮我", "麻烦", "请"):\n            if normalized.startswith(prefix):\n                normalized = normalized[len(prefix):]\n                break\n        for suffix in ("一下", "吧", "呢"):\n            if normalized.endswith(suffix):\n                normalized = normalized[:-len(suffix)]\n                break\n        for intent, phrases in cls.CONTROL_PHRASES.items():\n            if normalized in phrases:\n                return intent\n        return None\n'''
if source.count(old_constants) != 1:
    raise SystemExit('control constants anchor mismatch')
source=source.replace(old_constants,new_constants,1)

old_risk='''    def is_risky(self, text: str) -> str | None:\n        lowered = text.lower()\n        patterns = {\n            "production_change": ("生产环境", "production", "prod ", "上线", "部署到生产"),\n            "destructive_change": ("删除数据库", "drop database", "清空数据", "永久删除", "force push"),\n            "secret_operation": ("密码", "密钥", "token", "secret", "private key"),\n            "billing_operation": ("付款", "付费", "购买", "billing", "purchase"),\n        }\n        for reason, words in patterns.items():\n            if any(word in lowered for word in words):\n                return reason\n        return None\n'''
new_risk='''    def is_risky(self, text: str) -> str | None:\n        lowered = text.lower()\n        negative_safety = (\n            r"(?:不要|不得|禁止|避免|无需|不需要|不能|不可)[^。；;\\n]{0,80}"\n            r"(?:生产环境|production|数据库|database|密码|密钥|token|secret|private key|付款|付费|购买)",\n            r"(?:do not|don't|never|must not)[^.;\\n]{0,100}"\n            r"(?:production|database|password|token|secret|private key|billing|purchase)",\n        )\n        for pattern in negative_safety:\n            lowered = re.sub(pattern, "", lowered, flags=re.IGNORECASE)\n        patterns = {\n            "production_change": (\n                r"生产环境", r"部署到生产", r"发布到生产", r"上线",\n                r"production", r"deploy to prod", r"deploy to production",\n            ),\n            "destructive_change": (\n                r"删除数据库", r"清空数据", r"永久删除", r"drop database", r"force push",\n            ),\n            "secret_operation": (\n                r"(?:读取|查看|显示|输出|打印|修改|更新|写入|替换|轮换|使用|获取|上传|提交|暴露)"\n                r"[^。；;\\n]{0,30}(?:密码|密钥|token|secret|private key)",\n                r"(?:密码|密钥|token|secret|private key)[^。；;\\n]{0,30}"\n                r"(?:读取|查看|显示|输出|打印|修改|更新|写入|替换|轮换|使用|获取|上传|提交|暴露)",\n                r"(?:read|show|print|modify|update|write|rotate|use|fetch|upload|commit|expose)"\n                r"[^.;\\n]{0,40}(?:password|token|secret|private key)",\n            ),\n            "billing_operation": (r"付款", r"付费", r"购买", r"billing", r"purchase"),\n        }\n        for reason, expressions in patterns.items():\n            if any(re.search(expression, lowered, flags=re.IGNORECASE) for expression in expressions):\n                return reason\n        return None\n'''
if source.count(old_risk) != 1:
    raise SystemExit('risk anchor mismatch')
source=source.replace(old_risk,new_risk,1)

old_control='''        text = user_message.strip()\n        lowered = text.lower()\n        if any(word in lowered for word in self.HELP_WORDS):\n            return ProviderResult(\n                intent="help",\n                assistant_message="你可以直接告诉我：哪个项目需要完成什么开发目标。我会自行规划、实现、测试和交付。也可以说“查看进度”“停止任务”或“重试”。",\n            )\n        if any(word in lowered for word in self.CANCEL_WORDS):\n            if not session.get("current_task_id"):\n                return ProviderResult(intent="clarify", assistant_message="当前会话没有正在处理的任务。请先告诉我要完成什么开发工作。")\n            return ProviderResult(intent="cancel", assistant_message="我会安全停止当前任务，并保留完整审计记录。")\n        if any(word in lowered for word in self.RETRY_WORDS):\n            if not session.get("current_task_id"):\n                return ProviderResult(intent="clarify", assistant_message="当前会话没有可重试的任务。")\n            return ProviderResult(intent="retry", assistant_message="我会为当前终态任务创建一次显式重试，并继续在同一会话中跟踪。")\n        if any(word in lowered for word in self.STATUS_WORDS):\n            if not session.get("current_task_id"):\n                return ProviderResult(intent="chat", assistant_message="当前会话还没有任务。直接告诉我需要完成的开发目标即可。")\n            return ProviderResult(intent="status", assistant_message="我正在读取当前任务的最新状态。")\n'''
new_control='''        text = user_message.strip()\n        control_intent = self.control_intent(text)\n        if control_intent == "help":\n            return ProviderResult(\n                intent="help",\n                assistant_message="你可以直接告诉我：哪个项目需要完成什么开发目标。我会自行规划、实现、测试和交付。也可以说“查看进度”“停止任务”或“重试”。",\n            )\n        if control_intent == "cancel":\n            if not session.get("current_task_id"):\n                return ProviderResult(intent="clarify", assistant_message="当前会话没有正在处理的任务。请先告诉我要完成什么开发工作。")\n            return ProviderResult(intent="cancel", assistant_message="我会安全停止当前任务，并保留完整审计记录。")\n        if control_intent == "retry":\n            if not session.get("current_task_id"):\n                return ProviderResult(intent="clarify", assistant_message="当前会话没有可重试的任务。")\n            return ProviderResult(intent="retry", assistant_message="我会为当前终态任务创建一次显式重试，并继续在同一会话中跟踪。")\n        if control_intent == "status":\n            if not session.get("current_task_id"):\n                return ProviderResult(intent="chat", assistant_message="当前会话还没有任务。直接告诉我需要完成的开发目标即可。")\n            return ProviderResult(intent="status", assistant_message="我正在读取当前任务的最新状态。")\n'''
if source.count(old_control) != 1:
    raise SystemExit('analyze control anchor mismatch')
source=source.replace(old_control,new_control,1)

old_explicit='''def explicit_control_intent(text: str) -> bool:\n    lowered = text.lower()\n    provider = DeterministicFallbackProvider()\n    groups = [provider.STATUS_WORDS, provider.CANCEL_WORDS, provider.RETRY_WORDS, provider.HELP_WORDS]\n    return any(word in lowered for group in groups for word in group)\n'''
new_explicit='''def explicit_control_intent(text: str) -> bool:\n    return DeterministicFallbackProvider.control_intent(text) is not None\n'''
if source.count(old_explicit) != 1:
    raise SystemExit('explicit control anchor mismatch')
source=source.replace(old_explicit,new_explicit,1)

import_anchor='''    extract_router_result,\n    validate_provider_result,\n)\n'''
import_replacement='''    explicit_control_intent,\n    extract_router_result,\n    validate_provider_result,\n)\n'''
if tests.count(import_anchor) != 1:
    raise SystemExit('test import anchor mismatch')
tests=tests.replace(import_anchor,import_replacement,1)

test_anchor='''    def test_risky_request_requires_confirmation(self) -> None:\n'''
new_tests='''    def test_long_goal_with_status_code_is_not_control_command(self) -> None:\n        message = (\n            "给 Demo Project 增加一个只读 GET /capabilities 接口，"\n            "补充 pytest 覆盖接口状态码和字段契约，完成后提交并推送。"\n        )\n        self.assertFalse(explicit_control_intent(message))\n        result = self.provider.analyze(\n            session=self.session,\n            user_message=message,\n            projects=self.projects,\n            current_task=None,\n        )\n        self.assertEqual(result.intent, "create_task")\n\n    def test_negated_secret_constraint_is_not_risky(self) -> None:\n        message = "不要修改 ORIS 平台代码或任何密钥。"\n        self.assertIsNone(self.provider.is_risky(message))\n\n    def test_polite_exact_control_commands_remain_deterministic(self) -> None:\n        self.assertTrue(explicit_control_intent("请查看进度一下"))\n        self.assertTrue(explicit_control_intent("请停止当前任务"))\n        self.assertFalse(explicit_control_intent("补充接口状态码测试并提交"))\n\n'''+test_anchor
if tests.count(test_anchor) != 1:
    raise SystemExit('test insertion anchor mismatch')
tests=tests.replace(test_anchor,new_tests,1)

source_path.write_text(source,encoding='utf-8')
test_path.write_text(tests,encoding='utf-8')
PY
[ "$?" -eq 0 ] || fail "source_patch_failed" "INSPECT_PATCH_ANCHORS"
PATCH_RESULT="PASS"

python3 -m py_compile "$SOURCE" scripts/dev_employee_agent_harness.py scripts/dev_employee_chat_orchestrator.py >> "$RUN_LOG" 2>&1 || fail "py_compile_failed" "FIX_INTENT_BOUNDARY_CODE"
STATIC_CHECKS="PASS"

python3 -m pytest -q \
  tests/test_dev_employee_openclaw_provider.py \
  tests/test_dev_employee_agent_harness.py \
  tests/test_dev_employee_chat_orchestrator.py \
  tests/test_dev_employee_web_console_v3.py >> "$RUN_LOG" 2>&1 || fail "intent_boundary_tests_failed" "FIX_INTENT_BOUNDARY_TESTS"
TEST_RESULT="PASS"

python3 - <<'PY' >> "$RUN_LOG" 2>&1
from scripts.dev_employee_openclaw_provider import DeterministicFallbackProvider, explicit_control_intent
message=(
    "给 oris-final-acceptance-api 增加一个只读 GET /capabilities 接口，返回 service、storage 和 features 三个字段；"
    "features 至少包含 task_crud、filtering 和 stats。补充 pytest 覆盖接口状态码和字段契约，更新 README 的 API 列表，"
    "运行 py_compile 和 pytest，完成后提交并推送。不要修改 ORIS 平台代码或任何密钥。"
)
provider=DeterministicFallbackProvider()
projects={"oris-final-acceptance-api":{"name":"ORIS Final Acceptance API","forbidden_scope":[".env","secrets"]}}
session={"selected_project":None,"current_task_id":None,"messages":[]}
assert explicit_control_intent(message) is False
assert provider.is_risky(message) is None
result=provider.analyze(session=session,user_message=message,projects=projects,current_task=None)
assert result.intent == "create_task", result
assert result.project_key == "oris-final-acceptance-api"
for command, expected in [("查看进度","status"),("请查看进度一下","status"),("停止任务","cancel"),("重试","retry"),("帮助","help")]:
    assert provider.control_intent(command) == expected, (command,provider.control_intent(command))
print("REGRESSION_MESSAGE=PASS")
print("CONTROL_COMMANDS=PASS")
print("NEGATED_SECRET_POLICY=PASS")
PY
[ "$?" -eq 0 ] || fail "exact_message_regression_failed" "FIX_INTENT_CLASSIFIER"
REGRESSION_MESSAGE="PASS"
CONTROL_COMMANDS="PASS"
NEGATED_SECRET_POLICY="PASS"

git add -- "$SOURCE" "$TEST_FILE" >> "$RUN_LOG" 2>&1 || fail "code_git_add_failed" "INSPECT_ORIS_GIT_STATE"
git commit -m "fix(dev-employee): harden conversational intent boundaries" >> "$RUN_LOG" 2>&1 || fail "code_commit_failed" "INSPECT_ORIS_GIT_STATE"
git push origin main >> "$RUN_LOG" 2>&1 || fail "code_push_failed" "RESOLVE_GITHUB_PUSH"
CODE_COMMIT="$(git rev-parse HEAD)"

systemctl --user restart oris-dev-employee-web-console.service >> "$RUN_LOG" 2>&1 || fail "web_service_restart_failed" "INSPECT_WEB_CONSOLE_SERVICE"
sleep 3
[ "$(service_state oris-dev-employee-web-console.service)" = "active" ] || fail "web_service_not_active" "INSPECT_WEB_CONSOLE_SERVICE"
SERVICE_RESTART="PASS"

HEALTH="$(curl -fsS http://127.0.0.1:18893/health 2>/dev/null || true)"
python3 - "$HEALTH" <<'PY' >> "$RUN_LOG" 2>&1
import json,sys
p=json.loads(sys.argv[1])
assert p.get('service') == 'dev_employee_web_console_v5'
assert p.get('agent_harness_enabled') is True
assert p.get('openclaw_provider_configured') is True
PY
[ "$?" -eq 0 ] || fail "web_health_failed" "INSPECT_WEB_CONSOLE_SERVICE"
WEB_HEALTH="PASS"

FINAL_PRODUCT_SHA="$(git -C "$PRODUCT" rev-parse HEAD 2>/dev/null || true)"
FINAL_PRODUCT_REMOTE="$(git -C "$PRODUCT" ls-remote origin refs/heads/main 2>/dev/null | awk '{print $1}' | head -n1)"
[ "$FINAL_PRODUCT_SHA" = "$BASE_PRODUCT_SHA" ] && [ "$FINAL_PRODUCT_REMOTE" = "$BASE_PRODUCT_SHA" ] || fail "product_sha_changed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_SHA_UNCHANGED="PASS"
[ -z "$(git -C "$PRODUCT" status --porcelain --untracked-files=no)" ] || fail "product_worktree_changed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_WORKTREE_CLEAN="PASS"

RESULT="PASS"
NEXT_ACTION="RETRY_CONTROLLED_BROWSER_TASK_ONCE"
write_evidence
commit_log || { RESULT="FAILED"; FAILURE_CODE="evidence_push_failed"; NEXT_ACTION="RESOLVE_EVIDENCE_PUSH"; }
summary
[ "$RESULT" = "PASS" ] && exit 0
exit 1
