#!/usr/bin/env bash

TASK_ID="commercial-openclaw-native-plugin-install-20260618"
ORIS_REPO="/home/admin/projects/oris"
BASE_INSTALLER_REL="scripts/dev_employee_install_openclaw_native_plugin_tools_disabled_20260618.sh"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TMP_ROOT="$(mktemp -d /tmp/oris-openclaw-plugin-install-v3-${STAMP}-XXXXXX)"
PATCHED_INSTALLER="$TMP_ROOT/dev_employee_install_openclaw_native_plugin_tools_disabled_patched.sh"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

summary_fail() {
  local code="$1"
  local action="$2"
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=$code"
  echo "INSTALLER_VERSION=V3_AGENT_END_POLICY_AWARE"
  echo "PLUGIN_INSTALLED_OR_ENABLED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=$action"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit 1
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  summary_fail "wrong_linux_user" "RUN_AS_ADMIN"
fi
for cmd in git python3 bash sha256sum; do
  command -v "$cmd" >/dev/null 2>&1 || summary_fail "required_tool_missing_$cmd" "RESTORE_REQUIRED_HOST_TOOL"
done
[ -d "$ORIS_REPO/.git" ] || summary_fail "oris_repo_missing" "RESTORE_ORIS_REPOSITORY"

git -C "$ORIS_REPO" fetch origin main >/dev/null 2>&1 || summary_fail "oris_fetch_failed" "REPAIR_GITHUB_CONNECTIVITY"

STATUS_BEFORE_FILE="$TMP_ROOT/oris-status-before.bin"
STATUS_AFTER_FILE="$TMP_ROOT/oris-status-after.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$STATUS_BEFORE_FILE" 2>/dev/null || summary_fail "oris_status_capture_failed" "INSPECT_ORIS_REPOSITORY"
STATUS_BEFORE_SHA="$(sha256sum "$STATUS_BEFORE_FILE" | awk '{print $1}')"

if ! git -C "$ORIS_REPO" show "origin/main:$BASE_INSTALLER_REL" > "$PATCHED_INSTALLER" 2>/dev/null; then
  summary_fail "base_installer_not_found_on_origin_main" "PULL_ORIS_MAIN_AND_RETRY"
fi

python3 - "$PATCHED_INSTALLER" <<'PY_PATCH'
import sys
from pathlib import Path

path=Path(sys.argv[1])
text=path.read_text(encoding='utf-8')

def replace_once(old,new,label):
    global text
    if old not in text:
        raise SystemExit(f"expected fragment not found: {label}")
    text=text.replace(old,new,1)

replace_once(
    'openclaw plugins uninstall "$PLUGIN_ID" >> "$RUN_LOG" 2>&1 || true',
    'openclaw plugins uninstall "$PLUGIN_ID" --force >> "$RUN_LOG" 2>&1 || true',
    'automatic rollback uninstall',
)
replace_once(
    "elif low in {'hooks','registeredhooks','hooknames'}: add(x,hooks)",
    "elif low in {'hooks','registeredhooks','hooknames','typedhooks','customhooks'}: add(x,hooks)",
    'typed hook parser',
)
replace_once(
    'TOOLS_DENY_APPLIED="NO"\nTOOLS_ALLOW_UNCHANGED="NO"',
    'TOOLS_DENY_APPLIED="NO"\nCONVERSATION_ACCESS_POLICY="NO"\nTOOLS_ALLOW_UNCHANGED="NO"',
    'policy state variable',
)
replace_once(
    'echo "TOOLS_DENY_APPLIED=$TOOLS_DENY_APPLIED"\n  echo "TOOLS_ALLOW_UNCHANGED=$TOOLS_ALLOW_UNCHANGED"',
    'echo "TOOLS_DENY_APPLIED=$TOOLS_DENY_APPLIED"\n  echo "CONVERSATION_ACCESS_POLICY=$CONVERSATION_ACCESS_POLICY"\n  echo "TOOLS_ALLOW_UNCHANGED=$TOOLS_ALLOW_UNCHANGED"',
    'policy summary',
)
replace_once(
    'python3 - "$OPENCLAW_CONFIG" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<\'PY_DENY\'\nimport json,os,sys\nfrom pathlib import Path\npath=Path(sys.argv[1]); names=sys.argv[2:]',
    'python3 - "$OPENCLAW_CONFIG" "$PLUGIN_ID" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<\'PY_DENY\'\nimport json,os,sys\nfrom pathlib import Path\npath=Path(sys.argv[1]); plugin_id=sys.argv[2]; names=sys.argv[3:]',
    'deny invocation',
)
replace_once(
    "tools['deny']=deny\ntmp=path.with_name(path.name+'.oris-plugin.tmp')",
    "tools['deny']=deny\nplugins=data.setdefault('plugins',{})\nif not isinstance(plugins,dict): raise SystemExit(4)\nentries=plugins.setdefault('entries',{})\nif not isinstance(entries,dict): raise SystemExit(5)\nentry=entries.setdefault(plugin_id,{})\nif not isinstance(entry,dict): raise SystemExit(6)\nhooks=entry.setdefault('hooks',{})\nif not isinstance(hooks,dict): raise SystemExit(7)\nhooks['allowConversationAccess']=True\ntmp=path.with_name(path.name+'.oris-plugin.tmp')",
    'conversation access config mutation',
)
replace_once(
    'TOOLS_DENY_APPLIED="YES"\n\nopenclaw plugins install',
    'TOOLS_DENY_APPLIED="YES"\nCONVERSATION_ACCESS_POLICY="YES"\n\nopenclaw plugins install',
    'policy applied state',
)
replace_once(
    'python3 - "$OPENCLAW_CONFIG" "$TMP_ROOT/config-after-safe.json" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<\'PY_CONFIG_AFTER\'\nimport hashlib,json,sys\nfrom pathlib import Path\ndata=json.loads(Path(sys.argv[1]).read_text(encoding=\'utf-8\'))\nnames=sys.argv[3:6]',
    'python3 - "$OPENCLAW_CONFIG" "$TMP_ROOT/config-after-safe.json" "$PLUGIN_ID" "$TOOL_1" "$TOOL_2" "$TOOL_3" <<\'PY_CONFIG_AFTER\'\nimport hashlib,json,sys\nfrom pathlib import Path\ndata=json.loads(Path(sys.argv[1]).read_text(encoding=\'utf-8\'))\nplugin_id=sys.argv[3]\nnames=sys.argv[4:7]',
    'postinstall policy invocation',
)
replace_once(
    "deny=tools.get('deny') if isinstance(tools.get('deny'),list) else []\npayload={",
    "deny=tools.get('deny') if isinstance(tools.get('deny'),list) else []\nplugins=data.get('plugins') if isinstance(data.get('plugins'),dict) else {}\nentries=plugins.get('entries') if isinstance(plugins.get('entries'),dict) else {}\nentry=entries.get(plugin_id) if isinstance(entries.get(plugin_id),dict) else {}\nhooks=entry.get('hooks') if isinstance(entry.get('hooks'),dict) else {}\npayload={",
    'postinstall policy read',
)
replace_once(
    "'all_expected_denied':all(name in deny for name in names),\n 'denied_tools':[name for name in names if name in deny],",
    "'all_expected_denied':all(name in deny for name in names),\n 'conversation_access_policy':hooks.get('allowConversationAccess') is True,\n 'denied_tools':[name for name in names if name in deny],",
    'postinstall policy payload',
)
replace_once(
    'TOOLS_EFFECTIVELY_DENIED="$(python3 -c \'import json,sys; print("YES" if json.load(open(sys.argv[1]))["all_expected_denied"] else "NO")\' "$TMP_ROOT/config-after-safe.json")"\nif [ "$AUTH_MODE"',
    'TOOLS_EFFECTIVELY_DENIED="$(python3 -c \'import json,sys; print("YES" if json.load(open(sys.argv[1]))["all_expected_denied"] else "NO")\' "$TMP_ROOT/config-after-safe.json")"\nCONVERSATION_ACCESS_POLICY="$(python3 -c \'import json,sys; print("YES" if json.load(open(sys.argv[1]))["conversation_access_policy"] else "NO")\' "$TMP_ROOT/config-after-safe.json")"\n[ "$CONVERSATION_ACCESS_POLICY" = "YES" ] || fail_now "agent_end_conversation_access_policy_missing" "ROLL_BACK_PLUGIN_INSTALL"\nif [ "$AUTH_MODE"',
    'postinstall policy assertion',
)
replace_once(
    'export TASK_ID STAMP RESULT FAILURE_CODE SOURCE_COMMIT VALIDATED_PLUGIN_TREE_MATCH OPENCLAW_VERSION NODE_VERSION NPM_VERSION NPM_INSTALL TSC_BUILD UNIT_TESTS MIXED_PLUGIN_VALIDATE NPM_PACK ARTIFACT_SHA256 CONFIG_BACKUP_CREATED TOOLS_DENY_APPLIED TOOLS_ALLOW_UNCHANGED',
    'export TASK_ID STAMP RESULT FAILURE_CODE SOURCE_COMMIT VALIDATED_PLUGIN_TREE_MATCH OPENCLAW_VERSION NODE_VERSION NPM_VERSION NPM_INSTALL TSC_BUILD UNIT_TESTS MIXED_PLUGIN_VALIDATE NPM_PACK ARTIFACT_SHA256 CONFIG_BACKUP_CREATED TOOLS_DENY_APPLIED CONVERSATION_ACCESS_POLICY TOOLS_ALLOW_UNCHANGED',
    'export policy state',
)
replace_once(
    "'tools_deny_applied':os.environ['TOOLS_DENY_APPLIED']=='YES',\n   'tools_allow_unchanged'",
    "'tools_deny_applied':os.environ['TOOLS_DENY_APPLIED']=='YES',\n   'conversation_access_policy':os.environ['CONVERSATION_ACCESS_POLICY']=='YES',\n   'tools_allow_unchanged'",
    'evidence policy state',
)
replace_once(
    'echo "tools_deny_applied=$TOOLS_DENY_APPLIED"\n  echo "tools_allow_unchanged=$TOOLS_ALLOW_UNCHANGED"',
    'echo "tools_deny_applied=$TOOLS_DENY_APPLIED"\n  echo "conversation_access_policy=$CONVERSATION_ACCESS_POLICY"\n  echo "tools_allow_unchanged=$TOOLS_ALLOW_UNCHANGED"',
    'log policy state',
)

path.write_text(text,encoding='utf-8')
PY_PATCH
if [ "$?" -ne 0 ]; then
  summary_fail "installer_patch_failed" "INSPECT_BASE_INSTALLER_VERSION"
fi

chmod 700 "$PATCHED_INSTALLER"
bash -n "$PATCHED_INSTALLER" >/dev/null 2>&1 || summary_fail "patched_installer_syntax_failed" "INSPECT_INSTALLER_PATCH"

bash "$PATCHED_INSTALLER"
INNER_RC="$?"

git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$STATUS_AFTER_FILE" 2>/dev/null || summary_fail "oris_status_recapture_failed" "INSPECT_ORIS_REPOSITORY"
STATUS_AFTER_SHA="$(sha256sum "$STATUS_AFTER_FILE" | awk '{print $1}')"
if [ "$STATUS_BEFORE_SHA" != "$STATUS_AFTER_SHA" ]; then
  echo "===== SUMMARY ====="
  echo "RESULT=FAILED"
  echo "TASK_ID=$TASK_ID"
  echo "FAILURE_CODE=oris_existing_worktree_changed_during_install_wrapper"
  echo "INSTALLER_VERSION=V3_AGENT_END_POLICY_AWARE"
  echo "ORIS_EXISTING_WORKTREE_PRESERVED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "NEXT_ACTION=INSPECT_UNEXPECTED_ORIS_WORKTREE_CHANGE"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
  exit 1
fi
exit "$INNER_RC"
