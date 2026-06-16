#!/usr/bin/env bash

# Read-only discovery for the existing native OpenClaw UI and effective Nginx routing.
# This script does not change Nginx, systemd services, OpenClaw, the ORIS queue,
# or any product repository. It only commits sanitized discovery evidence to ORIS.

TASK_ID="commercial-native-openclaw-ui-20260617"
ORIS_REPO="/home/admin/projects/oris"
PRODUCT_REPO="/home/admin/projects/oris-final-acceptance-api"
DOMAIN="control.orisfy.com"
OPENCLAW_PORT="18789"
WEB_CONSOLE_PORT="18893"
INTAKE_PORT="18892"
EXPECTED_PRODUCT_COMMIT="927f1968cc86bfd5213670f4eaa171fc1a3be620"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR_REL="logs/dev_employee/native_openclaw_ui_discovery"
EVIDENCE_LOG_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-discovery-$STAMP.log"
EVIDENCE_JSON_REL="$EVIDENCE_DIR_REL/native-openclaw-ui-discovery-$STAMP.json"
TMP_ROOT="$(mktemp -d "/tmp/oris-native-openclaw-discovery-${STAMP}-XXXXXX")"
RUN_LOG="$TMP_ROOT/discovery.log"
RESULT_JSON="$TMP_ROOT/discovery.json"
NGINX_DUMP="$TMP_ROOT/nginx-sanitized.txt"
NGINX_JSON="$TMP_ROOT/nginx-analysis.json"
CONFIG_JSON="$TMP_ROOT/openclaw-config-keys.json"
UI_JSON="$TMP_ROOT/openclaw-ui-signals.json"
QUEUE_JSON="$TMP_ROOT/active-queue.json"
BASELINE_JSON="$TMP_ROOT/repository-baselines.json"
ROOT_HEADERS="$TMP_ROOT/openclaw-root.headers"
ROOT_BODY="$TMP_ROOT/openclaw-root.body"
SPA_HEADERS="$TMP_ROOT/openclaw-spa.headers"
SPA_BODY="$TMP_ROOT/openclaw-spa.body"
ASSET_DIR="$TMP_ROOT/assets"
WORKTREE="$TMP_ROOT/evidence-worktree"

RESULT="FAILED"
FAILURE_CODE=""
DISCOVERY_COMPLETE="NO"
OPENCLAW_SCOPE="unknown"
OPENCLAW_SERVICE_STATE="unknown"
OPENCLAW_VERSION="unknown"
OPENCLAW_ROOT_STATUS="000"
SPA_FALLBACK="INCONCLUSIVE"
WEBSOCKET_CANDIDATE_COUNT="0"
NGINX_T_RESULT="NOT_RUN"
EFFECTIVE_HTTP_CONFIG="unknown"
EFFECTIVE_HTTPS_CONFIG="unknown"
CURRENT_ROOT_UPSTREAM="unknown"
CURRENT_ADMIN_UPSTREAM="unknown"
DUPLICATE_SERVER_BLOCKS="unknown"
ACTIVE_QUEUE_COUNT="unknown"
PRODUCT_HEAD="unknown"
PRODUCT_REMOTE_MAIN="unknown"
PRODUCT_CLEAN="unknown"
INTAKE_LOOPBACK_ONLY="unknown"
SECRET_SCAN="NOT_RUN"
EVIDENCE_COMMIT=""
EVIDENCE_REMOTE_VERIFIED="NO"
NEXT_ACTION="INSPECT_DISCOVERY_FAILURE"

umask 077
mkdir -p "$ASSET_DIR"
: > "$RUN_LOG"

cleanup() {
  if [ -d "$WORKTREE" ]; then
    git -C "$ORIS_REPO" worktree remove --force "$WORKTREE" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT

log() {
  printf '%s\n' "$*" >> "$RUN_LOG"
}

section() {
  log ""
  log "===== $* ====="
}

sanitize_stream() {
  python3 -c '
import re, sys
patterns = [
    (re.compile(r"(?i)(authorization\s*:\s*(?:bearer|basic)\s+)[^\s;]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(\bauthorization\b\s+[\"\\\x27]?(?:bearer|basic)\s+)[^\s;\"\\\x27]+"), r"\1<redacted>"),
    (re.compile(r"(?i)((?:--)?(?:token|api[-_]?key|secret|password|credential|client[-_]?secret|access[-_]?key)(?:=|\s+))[^\s,;]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(\b(?:token|api[-_]?key|secret|password|credential|client[-_]?secret|access[-_]?key)\b\s*[:=]\s*)[^\s,;]+"), r"\1<redacted>"),
    (re.compile(r"(?i)(cookie\s*:\s*).*$"), r"\1<redacted>"),
    (re.compile(r"(?i)(https?://[^:/\s]+:)[^@/\s]+@"), r"\1<redacted>@"),
    (re.compile(r"(?i)([?&](?:token|key|secret|password|signature|sig)=)[^&#\s]+"), r"\1<redacted>"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "<redacted-private-key-marker>"),
]
for line in sys.stdin:
    for pattern, replacement in patterns:
        line = pattern.sub(replacement, line)
    sys.stdout.write(line)
'
}

json_get() {
  local file="$1"
  local expression="$2"
  python3 - "$file" "$expression" <<'PY'
import json, sys
from pathlib import Path
path=Path(sys.argv[1])
expr=sys.argv[2]
try:
    data=json.loads(path.read_text(encoding="utf-8"))
    value=data
    for part in expr.split("."):
        if isinstance(value, list):
            value=value[int(part)]
        else:
            value=value.get(part)
    if value is None:
        print("")
    elif isinstance(value, bool):
        print("YES" if value else "NO")
    elif isinstance(value, (dict, list)):
        print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
    else:
        print(value)
except Exception:
    print("")
PY
}

header_summary() {
  local header_file="$1"
  python3 - "$header_file" <<'PY'
import re, sys
from pathlib import Path
p=Path(sys.argv[1])
if not p.exists():
    raise SystemExit
text=p.read_text(encoding="utf-8", errors="replace")
blocks=re.split(r"\r?\n\r?\n", text.strip())
block=blocks[-1] if blocks else text
allowed={"content-type","content-length","cache-control","location","server","upgrade","connection","strict-transport-security","content-security-policy","x-frame-options","x-content-type-options"}
cookies=[]
for line in block.splitlines():
    if ":" not in line:
        continue
    name, value=line.split(":",1)
    key=name.strip().lower()
    value=value.strip()
    if key == "set-cookie":
        cookie=value.split(";",1)[0].split("=",1)[0].strip()
        if cookie and cookie not in cookies:
            cookies.append(cookie)
    elif key in allowed:
        if key == "location":
            value=value.split("?",1)[0]
        print(f"HTTP_HEADER_{key.upper().replace(chr(45),chr(95))}={value[:500]}")
print("HTTP_SET_COOKIE_NAMES=" + ",".join(cookies))
PY
}

final_summary() {
  echo "===== SUMMARY ====="
  echo "RESULT=$RESULT"
  echo "TASK_ID=$TASK_ID"
  echo "DISCOVERY_COMPLETE=$DISCOVERY_COMPLETE"
  echo "FAILURE_CODE=$FAILURE_CODE"
  echo "OPENCLAW_SCOPE=$OPENCLAW_SCOPE"
  echo "OPENCLAW_SERVICE_STATE=$OPENCLAW_SERVICE_STATE"
  echo "OPENCLAW_VERSION=$OPENCLAW_VERSION"
  echo "OPENCLAW_ROOT_STATUS=$OPENCLAW_ROOT_STATUS"
  echo "SPA_FALLBACK=$SPA_FALLBACK"
  echo "WEBSOCKET_CANDIDATE_COUNT=$WEBSOCKET_CANDIDATE_COUNT"
  echo "NGINX_T=$NGINX_T_RESULT"
  echo "EFFECTIVE_HTTP_CONFIG=$EFFECTIVE_HTTP_CONFIG"
  echo "EFFECTIVE_HTTPS_CONFIG=$EFFECTIVE_HTTPS_CONFIG"
  echo "CURRENT_ROOT_UPSTREAM=$CURRENT_ROOT_UPSTREAM"
  echo "CURRENT_ADMIN_UPSTREAM=$CURRENT_ADMIN_UPSTREAM"
  echo "DUPLICATE_SERVER_BLOCKS=$DUPLICATE_SERVER_BLOCKS"
  echo "ACTIVE_QUEUE_COUNT=$ACTIVE_QUEUE_COUNT"
  echo "PRODUCT_HEAD=$PRODUCT_HEAD"
  echo "PRODUCT_REMOTE_MAIN=$PRODUCT_REMOTE_MAIN"
  echo "PRODUCT_CLEAN=$PRODUCT_CLEAN"
  echo "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
  echo "SECRET_SCAN=$SECRET_SCAN"
  echo "CONFIG_OR_SERVICE_CHANGED=NO"
  echo "PRODUCT_TASK_SUBMITTED=NO"
  echo "EVIDENCE_LOG=$EVIDENCE_LOG_REL"
  echo "EVIDENCE_JSON=$EVIDENCE_JSON_REL"
  echo "EVIDENCE_COMMIT=$EVIDENCE_COMMIT"
  echo "EVIDENCE_REMOTE_VERIFIED=$EVIDENCE_REMOTE_VERIFIED"
  echo "NEXT_ACTION=$NEXT_ACTION"
  echo "SEND_TO_CHAT=THIS_SUMMARY_ONLY"
  echo "===== END SUMMARY ====="
}

fail_now() {
  FAILURE_CODE="$1"
  NEXT_ACTION="$2"
  RESULT="FAILED"
  DISCOVERY_COMPLETE="NO"
  final_summary
  exit 1
}

if [ "$(id -un 2>/dev/null)" != "admin" ]; then
  fail_now "wrong_linux_user" "RUN_AS_ADMIN"
fi

if [ ! -d "$ORIS_REPO/.git" ]; then
  fail_now "oris_repository_missing" "RESTORE_ORIS_REPOSITORY"
fi

if ! command -v python3 >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1; then
  fail_now "required_discovery_tool_missing" "INSTALL_REQUIRED_HOST_TOOLS_WITHOUT_CHANGING_OPENCLAW"
fi

if ! bash -n "$0" >/dev/null 2>&1; then
  fail_now "script_syntax_invalid" "REPAIR_DISCOVERY_SCRIPT"
fi

section "DISCOVERY CONTRACT"
log "CHECKED_AT=$(date -Is)"
log "TASK_ID=$TASK_ID"
log "MODE=READ_ONLY_DISCOVERY"
log "ORIS_REPO=$ORIS_REPO"
log "PRODUCT_REPO=$PRODUCT_REPO"
log "DOMAIN=$DOMAIN"
log "CONFIG_OR_SERVICE_CHANGED=NO"
log "PRODUCT_TASK_SUBMITTED=NO"
log "MAIN_WORKTREE_MUTATED_BY_DISCOVERY=NO"

section "ORIS MAIN WORKTREE BASELINE"
log "ORIS_HEAD=$(git -C "$ORIS_REPO" rev-parse HEAD 2>/dev/null || true)"
log "ORIS_BRANCH=$(git -C "$ORIS_REPO" branch --show-current 2>/dev/null || true)"
ORIS_TRACKED_DIRTY_COUNT="$(git -C "$ORIS_REPO" status --porcelain --untracked-files=no 2>/dev/null | wc -l | tr -d ' ')"
ORIS_UNTRACKED_COUNT="$(git -C "$ORIS_REPO" status --porcelain --untracked-files=all 2>/dev/null | awk '$1=="??"{n++} END{print n+0}')"
log "ORIS_TRACKED_DIRTY_COUNT=$ORIS_TRACKED_DIRTY_COUNT"
log "ORIS_UNTRACKED_COUNT=$ORIS_UNTRACKED_COUNT"
log "ORIS_REMOTE=$(git -C "$ORIS_REPO" remote get-url origin 2>/dev/null | sanitize_stream)"

section "OPENCLAW SYSTEMD UNIT"
SYSTEMCTL_PREFIX=()
if systemctl --user show openclaw-gateway.service -p LoadState --value 2>/dev/null | grep -qv '^not-found$'; then
  SYSTEMCTL_PREFIX=(systemctl --user)
  OPENCLAW_SCOPE="user"
elif systemctl show openclaw-gateway.service -p LoadState --value 2>/dev/null | grep -qv '^not-found$'; then
  SYSTEMCTL_PREFIX=(systemctl)
  OPENCLAW_SCOPE="system"
else
  log "OPENCLAW_UNIT_FOUND=NO"
  OPENCLAW_SCOPE="not_found"
fi

OPENCLAW_PID=""
OPENCLAW_FRAGMENT=""
if [ "$OPENCLAW_SCOPE" = "user" ] || [ "$OPENCLAW_SCOPE" = "system" ]; then
  OPENCLAW_SERVICE_STATE="$(${SYSTEMCTL_PREFIX[@]} is-active openclaw-gateway.service 2>/dev/null || true)"
  OPENCLAW_PID="$(${SYSTEMCTL_PREFIX[@]} show openclaw-gateway.service -p MainPID --value 2>/dev/null || true)"
  OPENCLAW_FRAGMENT="$(${SYSTEMCTL_PREFIX[@]} show openclaw-gateway.service -p FragmentPath --value 2>/dev/null || true)"
  log "OPENCLAW_UNIT_FOUND=YES"
  log "OPENCLAW_UNIT_SCOPE=$OPENCLAW_SCOPE"
  log "OPENCLAW_UNIT_ACTIVE_STATE=$OPENCLAW_SERVICE_STATE"
  ${SYSTEMCTL_PREFIX[@]} show openclaw-gateway.service \
    -p Id -p LoadState -p ActiveState -p SubState -p MainPID -p FragmentPath -p DropInPaths -p EnvironmentFiles \
    --no-pager 2>&1 | sanitize_stream >> "$RUN_LOG"
  EXEC_START_RAW="$(${SYSTEMCTL_PREFIX[@]} show openclaw-gateway.service -p ExecStart --value 2>/dev/null || true)"
  printf 'OPENCLAW_EXEC_START=%s\n' "$EXEC_START_RAW" | sanitize_stream >> "$RUN_LOG"
  ENV_RAW="$(${SYSTEMCTL_PREFIX[@]} show openclaw-gateway.service -p Environment --value 2>/dev/null || true)"
  printf '%s' "$ENV_RAW" | python3 -c '
import shlex, sys
raw=sys.stdin.read()
keys=[]
try:
    items=shlex.split(raw)
except Exception:
    items=raw.split()
for item in items:
    key=item.split("=",1)[0].strip()
    if key and key.replace("_","").isalnum() and key not in keys:
        keys.append(key)
print("OPENCLAW_UNIT_ENVIRONMENT_KEYS=" + ",".join(sorted(keys)))
' >> "$RUN_LOG"
else
  OPENCLAW_SERVICE_STATE="not_found"
fi

section "OPENCLAW PROCESS AND LISTENERS"
if printf '%s' "$OPENCLAW_PID" | grep -Eq '^[1-9][0-9]*$' && [ -d "/proc/$OPENCLAW_PID" ]; then
  ps -p "$OPENCLAW_PID" -o pid=,user=,lstart=,etime=,comm=,args= 2>/dev/null | sanitize_stream | sed 's/^/OPENCLAW_PROCESS=/' >> "$RUN_LOG"
  OPENCLAW_EXE="$(readlink -f "/proc/$OPENCLAW_PID/exe" 2>/dev/null || true)"
  log "OPENCLAW_PROCESS_EXE=$OPENCLAW_EXE"
  tr '\0' '\n' < "/proc/$OPENCLAW_PID/environ" 2>/dev/null | sed 's/=.*$//' | grep -E '^[A-Za-z_][A-Za-z0-9_]*$' | sort -u | paste -sd, - | sed 's/^/OPENCLAW_PROCESS_ENVIRONMENT_KEYS=/' >> "$RUN_LOG"
else
  log "OPENCLAW_PROCESS_FOUND=NO"
fi

if command -v ss >/dev/null 2>&1; then
  ss -ltnp 2>/dev/null | awk -v p=":$OPENCLAW_PORT" '$4 ~ p"$" || $4 ~ ":18791$" || $4 ~ ":18892$" || $4 ~ ":18893$" {print}' | sanitize_stream | sed 's/^/LISTENER=/' >> "$RUN_LOG"
  INTAKE_LISTENER="$(ss -ltn 2>/dev/null | awk -v p=":$INTAKE_PORT" '$4 ~ p"$" {print $4; exit}')"
  case "$INTAKE_LISTENER" in
    127.0.0.1:*|\[::1\]:*) INTAKE_LOOPBACK_ONLY="YES" ;;
    "") INTAKE_LOOPBACK_ONLY="NOT_LISTENING" ;;
    *) INTAKE_LOOPBACK_ONLY="NO" ;;
  esac
  log "INTAKE_LISTENER_ADDRESS=$INTAKE_LISTENER"
  log "INTAKE_LOOPBACK_ONLY=$INTAKE_LOOPBACK_ONLY"
else
  log "SS_COMMAND_AVAILABLE=NO"
  INTAKE_LOOPBACK_ONLY="INCONCLUSIVE"
fi

OPENCLAW_BIN=""
for candidate in "$(command -v openclaw 2>/dev/null || true)" "$HOME/.npm-global/bin/openclaw" "$HOME/.local/bin/openclaw" "/usr/local/bin/openclaw" "/usr/bin/openclaw"; do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then
    OPENCLAW_BIN="$candidate"
    break
  fi
done
if [ -n "$OPENCLAW_BIN" ]; then
  OPENCLAW_VERSION="$($OPENCLAW_BIN --version 2>&1 | head -n 2 | sanitize_stream | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g; s/[[:space:]]$//')"
  log "OPENCLAW_BINARY=$OPENCLAW_BIN"
  log "OPENCLAW_VERSION=$OPENCLAW_VERSION"
  "$OPENCLAW_BIN" --help 2>&1 | sanitize_stream | awk '/^[[:space:]]{2,}[A-Za-z0-9_-]+([,[:space:]]|$)/{gsub(/^[[:space:]]+/,""); print $1}' | tr '\n' ',' | sed 's/,$//; s/^/OPENCLAW_CLI_COMMANDS=/' >> "$RUN_LOG"
else
  log "OPENCLAW_BINARY=NOT_FOUND"
fi

section "OPENCLAW CONFIG KEY NAMES ONLY"
python3 - "$HOME" "$CONFIG_JSON" <<'PY'
import json, re, stat, sys
from pathlib import Path
home=Path(sys.argv[1])
out=Path(sys.argv[2])
roots=[home/".openclaw", home/".config/openclaw", home/".config/OpenClaw", Path("/etc/openclaw")]
allowed_ext={".json",".json5",".yaml",".yml",".toml",".ini",".conf",".env",".service",".properties"}
skip_parts={"node_modules","cache","logs","sessions","history","conversations","attachments","tmp","temp","runtime"}
key_re=re.compile(r"^\s*[\"']?([A-Za-z_][A-Za-z0-9_.-]*)[\"']?\s*[:=]", re.M)
files=[]
all_keys=set()
for root in roots:
    if not root.exists():
        continue
    for p in sorted(root.rglob("*")):
        try:
            if not p.is_file() or p.is_symlink():
                continue
            rel_parts={part.lower() for part in p.parts}
            if rel_parts & skip_parts:
                continue
            if p.suffix.lower() not in allowed_ext and p.name.lower() not in {"config","settings"}:
                continue
            size=p.stat().st_size
            if size > 1024*1024:
                continue
            text=p.read_text(encoding="utf-8", errors="replace")
            keys=set(key_re.findall(text))
            if p.suffix.lower()==".json":
                try:
                    data=json.loads(text)
                    def walk(v):
                        if isinstance(v, dict):
                            for k, child in v.items():
                                if isinstance(k, str):
                                    keys.add(k)
                                walk(child)
                        elif isinstance(v, list):
                            for child in v:
                                walk(child)
                    walk(data)
                except Exception:
                    pass
            all_keys.update(keys)
            files.append({"path":str(p),"mode":oct(stat.S_IMODE(p.stat().st_mode)),"size":size,"keys":sorted(keys)[:250]})
        except (OSError, PermissionError):
            continue
classes={
    "token":any("token" in k.lower() for k in all_keys),
    "device_pairing":any(any(x in k.lower() for x in ("pair","device")) for k in all_keys),
    "authentication":any(any(x in k.lower() for x in ("auth","credential","password","secret")) for k in all_keys),
    "session_history":any(any(x in k.lower() for x in ("session","history","conversation")) for k in all_keys),
    "websocket":any(any(x in k.lower() for x in ("websocket","socket","ws_","ws.")) for k in all_keys),
}
out.write_text(json.dumps({"roots_checked":[str(x) for x in roots],"files":files,"all_key_names":sorted(all_keys),"key_classes_present":classes},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY
python3 -m json.tool "$CONFIG_JSON" >> "$RUN_LOG" 2>/dev/null || log "CONFIG_KEY_SCAN=FAILED"

section "OPENCLAW SESSION AND HISTORY STORAGE NAMES"
for root in "$HOME/.openclaw" "$HOME/.config/openclaw" "$HOME/.config/OpenClaw"; do
  [ -d "$root" ] || continue
  find "$root" -maxdepth 5 \( -iname '*session*' -o -iname '*history*' -o -iname '*conversation*' -o -iname '*device*' -o -iname '*pair*' \) -printf '%y %m %s %p\n' 2>/dev/null | head -n 250 | sanitize_stream | sed 's/^/OPENCLAW_STORAGE_NAME=/' >> "$RUN_LOG"
done

section "OPENCLAW HTTP ROOT STATIC ASSETS AND SPA"
OPENCLAW_BASE="http://127.0.0.1:$OPENCLAW_PORT"
OPENCLAW_ROOT_STATUS="$(curl -sS --max-time 8 -D "$ROOT_HEADERS" -o "$ROOT_BODY" -w '%{http_code}' "$OPENCLAW_BASE/" 2>/dev/null || true)"
[ -n "$OPENCLAW_ROOT_STATUS" ] || OPENCLAW_ROOT_STATUS="000"
log "OPENCLAW_ROOT_STATUS=$OPENCLAW_ROOT_STATUS"
log "OPENCLAW_ROOT_BODY_SIZE=$(wc -c < "$ROOT_BODY" 2>/dev/null | tr -d ' ' || echo 0)"
log "OPENCLAW_ROOT_BODY_SHA256=$(sha256sum "$ROOT_BODY" 2>/dev/null | awk '{print $1}')"
header_summary "$ROOT_HEADERS" | sanitize_stream >> "$RUN_LOG"

python3 - "$ROOT_BODY" "$OPENCLAW_BASE" "$TMP_ROOT/asset-paths.txt" <<'PY'
import html.parser, sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit
body=Path(sys.argv[1]); base=sys.argv[2]; out=Path(sys.argv[3])
class P(html.parser.HTMLParser):
    def __init__(self): super().__init__(); self.paths=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        for key in ("src","href"):
            value=d.get(key)
            if not value: continue
            u=urlsplit(urljoin(base+"/",value))
            if u.hostname not in (None,"127.0.0.1","localhost"): continue
            path=u.path or "/"
            if path not in self.paths: self.paths.append(path)
p=P()
try: p.feed(body.read_text(encoding="utf-8",errors="replace"))
except Exception: pass
out.write_text("\n".join(p.paths[:60])+"\n",encoding="utf-8")
PY

ASSET_INDEX=0
while IFS= read -r asset_path; do
  [ -n "$asset_path" ] || continue
  ASSET_INDEX=$((ASSET_INDEX+1))
  SAFE_NAME="asset-$ASSET_INDEX"
  ASSET_HEADERS="$ASSET_DIR/$SAFE_NAME.headers"
  ASSET_BODY="$ASSET_DIR/$SAFE_NAME.body"
  ASSET_STATUS="$(curl -sS --max-time 8 -D "$ASSET_HEADERS" -o "$ASSET_BODY" -w '%{http_code}' "$OPENCLAW_BASE$asset_path" 2>/dev/null || true)"
  ASSET_TYPE="$(awk -F': *' 'tolower($1)=="content-type"{v=$2} END{gsub(/\r/,"",v); print v}' "$ASSET_HEADERS" 2>/dev/null)"
  ASSET_SIZE="$(wc -c < "$ASSET_BODY" 2>/dev/null | tr -d ' ' || echo 0)"
  log "OPENCLAW_ASSET_PATH=$asset_path status=${ASSET_STATUS:-000} content_type=$ASSET_TYPE size=$ASSET_SIZE"
  printf '%s\t%s\t%s\n' "$asset_path" "$ASSET_TYPE" "$ASSET_BODY" >> "$TMP_ROOT/assets-manifest.tsv"
  [ "$ASSET_INDEX" -ge 30 ] && break
done < "$TMP_ROOT/asset-paths.txt"
log "OPENCLAW_ASSET_COUNT=$ASSET_INDEX"

SPA_PATH="/_oris_readonly_spa_probe_$STAMP"
SPA_STATUS="$(curl -sS --max-time 8 -D "$SPA_HEADERS" -o "$SPA_BODY" -w '%{http_code}' "$OPENCLAW_BASE$SPA_PATH" 2>/dev/null || true)"
ROOT_SHA="$(sha256sum "$ROOT_BODY" 2>/dev/null | awk '{print $1}')"
SPA_SHA="$(sha256sum "$SPA_BODY" 2>/dev/null | awk '{print $1}')"
SPA_TYPE="$(awk -F': *' 'tolower($1)=="content-type"{v=$2} END{gsub(/\r/,"",v); print v}' "$SPA_HEADERS" 2>/dev/null)"
if [ "$OPENCLAW_ROOT_STATUS" = "200" ] && [ "$SPA_STATUS" = "200" ] && [ -n "$ROOT_SHA" ] && [ "$ROOT_SHA" = "$SPA_SHA" ]; then
  SPA_FALLBACK="YES"
elif [ "$SPA_STATUS" = "404" ]; then
  SPA_FALLBACK="NO"
else
  SPA_FALLBACK="INCONCLUSIVE"
fi
log "OPENCLAW_SPA_PROBE_PATH=$SPA_PATH"
log "OPENCLAW_SPA_PROBE_STATUS=${SPA_STATUS:-000}"
log "OPENCLAW_SPA_PROBE_CONTENT_TYPE=$SPA_TYPE"
log "OPENCLAW_SPA_ROOT_HASH_MATCH=$([ -n "$ROOT_SHA" ] && [ "$ROOT_SHA" = "$SPA_SHA" ] && echo YES || echo NO)"
log "OPENCLAW_SPA_FALLBACK=$SPA_FALLBACK"

section "OPENCLAW UI CAPABILITY AUTH AND WEBSOCKET SIGNALS"
python3 - "$ROOT_BODY" "$TMP_ROOT/assets-manifest.tsv" "$UI_JSON" <<'PY'
import json, re, sys
from pathlib import Path
from urllib.parse import urlsplit
root=Path(sys.argv[1]); manifest=Path(sys.argv[2]); out=Path(sys.argv[3])
parts=[]
try: parts.append(root.read_text(encoding="utf-8",errors="replace")[:2_000_000])
except Exception: pass
assets=[]; total=0
if manifest.exists():
    for line in manifest.read_text(encoding="utf-8",errors="replace").splitlines():
        cols=line.split("\t")
        if len(cols)!=3: continue
        path,ctype,filename=cols
        if not any(x in ctype.lower() for x in ("javascript","json","html")) and not path.endswith((".js",".mjs",".json")): continue
        p=Path(filename)
        try:
            size=p.stat().st_size
            if size>4_000_000 or total+size>12_000_000: continue
            parts.append(p.read_text(encoding="utf-8",errors="replace")); assets.append(path); total+=size
        except Exception: pass
text="\n".join(parts); lower=text.lower()
patterns={
 "new_conversation":["new conversation","new chat","create conversation","create session","new session"],
 "history_list":["conversation history","chat history","session history","conversation list","session list"],
 "conversation_switching":["switch conversation","select conversation","selectedsession","activesession","activeconversation"],
 "clear_archive_delete":["clear conversation","clear chat","delete conversation","archive conversation","delete session","archive session"],
 "device_pairing":["device pairing","pair device","pairing code","device code"],
 "token_auth":["access token","gateway token","bearer token","auth token"],
 "local_storage":["localstorage"],"session_storage":["sessionstorage"],"indexed_db":["indexeddb"],
}
signals={name:any(p in lower for p in pats) for name,pats in patterns.items()}
ws=set(); api=set()
for match in re.findall(r"wss?://[^\"'`\\\s<>()]+",text,flags=re.I):
    try:
        u=urlsplit(match)
        if u.path: ws.add(u.path.split("?",1)[0])
    except Exception: pass
for match in re.findall(r"new\s+WebSocket\s*\(\s*[\"'`]([^\"'`]+)",text,flags=re.I):
    if match.startswith("/"): ws.add(match.split("?",1)[0])
for match in re.findall(r"[\"'`](/(?:api/)?(?:ws|websocket|socket)(?:/[^\"'`?]*)?)[?\"'`]",text,flags=re.I): ws.add(match)
for match in re.findall(r"[\"'`](/(?:api|v1)/[A-Za-z0-9_./:-]{1,160})[?\"'`]",text): api.add(match.rstrip("/"))
ws={p for p in ws if re.fullmatch(r"/[A-Za-z0-9_./:${}-]{1,200}",p)}
api={p for p in api if re.fullmatch(r"/[A-Za-z0-9_./:${}-]{1,200}",p)}
out.write_text(json.dumps({"assets_scanned":assets,"bytes_scanned":total,"capability_signals":signals,"websocket_candidate_paths":sorted(ws)[:50],"api_candidate_paths":sorted(api)[:100],"interpretation":"Signals from installed UI assets are discovery evidence, not browser acceptance."},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY
python3 -m json.tool "$UI_JSON" >> "$RUN_LOG" 2>/dev/null || log "UI_SIGNAL_SCAN=FAILED"
WEBSOCKET_CANDIDATE_COUNT="$(json_get "$UI_JSON" websocket_candidate_paths | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null || echo 0)"

section "OPENCLAW WEBSOCKET HANDSHAKE PROBES"
python3 - "$UI_JSON" "$TMP_ROOT/ws-paths.txt" <<'PY'
import json, sys
from pathlib import Path
paths=[]
try: paths=json.loads(Path(sys.argv[1]).read_text()).get("websocket_candidate_paths",[])
except Exception: pass
for default in ("/ws","/api/ws","/websocket","/socket"):
    if default not in paths: paths.append(default)
Path(sys.argv[2]).write_text("\n".join(paths[:20])+"\n",encoding="utf-8")
PY
WS_PROBE_COUNT=0
while IFS= read -r ws_path; do
  [ -n "$ws_path" ] || continue
  WS_PROBE_COUNT=$((WS_PROBE_COUNT+1))
  WS_HEADERS="$TMP_ROOT/ws-$WS_PROBE_COUNT.headers"
  WS_CODE="$(curl -sS --http1.1 --max-time 6 -D "$WS_HEADERS" -o /dev/null -w '%{http_code}' -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: b3Jpcy1yZWFkb25seS1wcm9iZQ==' -H 'Origin: https://control.orisfy.com' "$OPENCLAW_BASE$ws_path" 2>/dev/null || true)"
  log "OPENCLAW_WS_PROBE_PATH=$ws_path status=${WS_CODE:-000}"
  header_summary "$WS_HEADERS" | grep -E 'HTTP_HEADER_(UPGRADE|CONNECTION|LOCATION)|HTTP_SET_COOKIE_NAMES' | sanitize_stream >> "$RUN_LOG"
  [ "$WS_PROBE_COUNT" -ge 20 ] && break
done < "$TMP_ROOT/ws-paths.txt"
log "OPENCLAW_WS_PROBE_COUNT=$WS_PROBE_COUNT"

section "DIRECT SERVICE HEALTH"
for target in "openclaw_root|http://127.0.0.1:$OPENCLAW_PORT/" "openclaw_health|http://127.0.0.1:$OPENCLAW_PORT/health" "openclaw_v1_health|http://127.0.0.1:$OPENCLAW_PORT/v1/health" "web_console_root|http://127.0.0.1:$WEB_CONSOLE_PORT/" "web_console_health|http://127.0.0.1:$WEB_CONSOLE_PORT/health" "intake_health|http://127.0.0.1:$INTAKE_PORT/health"; do
  name="${target%%|*}"; url="${target#*|}"
  code="$(curl -sS --max-time 5 -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
  log "DIRECT_HTTP_PROBE=$name status=${code:-000}"
done
for unit in openclaw-gateway.service oris-dev-employee-web-console.service oris-dev-employee-intake.service oris-dev-employee-bridge.service; do
  state="$(systemctl --user is-active "$unit" 2>/dev/null || systemctl is-active "$unit" 2>/dev/null || true)"
  log "SERVICE_STATE=$unit state=$state"
done

section "EFFECTIVE NGINX CONFIGURATION"
set -o pipefail
if sudo -n nginx -T 2>&1 | sanitize_stream > "$NGINX_DUMP"; then
  NGINX_T_RESULT="PASS"
elif nginx -T 2>&1 | sanitize_stream > "$NGINX_DUMP"; then
  NGINX_T_RESULT="PASS_NON_SUDO"
else
  NGINX_T_RESULT="FAILED"
fi
set +o pipefail
log "NGINX_T_RESULT=$NGINX_T_RESULT"
python3 - "$NGINX_DUMP" "$NGINX_JSON" "$DOMAIN" <<'PY'
import json, re, sys
from pathlib import Path
src=Path(sys.argv[1]); out=Path(sys.argv[2]); domain=sys.argv[3]
text=src.read_text(encoding="utf-8",errors="replace"); lines=text.splitlines()
files=[]; current="unknown"; file_line=0; records=[]
for global_line,line in enumerate(lines,1):
    m=re.match(r"# configuration file (.+):$",line)
    if m: current=m.group(1); file_line=0; files.append(current); continue
    file_line+=1; records.append((global_line,current,file_line,line))
def strip_line(s):
    s=re.sub(r"#.*$","",s); s=re.sub(r"\"(?:\\.|[^\"])*\"","\"\"",s); s=re.sub(r"'(?:\\.|[^'])*'","''",s); return s
servers=[]; i=0
while i<len(records):
    gl,fn,fl,line=records[i]
    if re.match(r"^\s*server\s*\{",strip_line(line)):
        start=i; depth=0; j=i
        while j<len(records):
            clean=strip_line(records[j][3]); depth+=clean.count("{")-clean.count("}")
            if j>i and depth<=0: break
            j+=1
        block=records[start:j+1]; block_text="\n".join(x[3] for x in block)
        names=[]
        for m in re.finditer(r"(?m)^\s*server_name\s+([^;]+);",block_text): names.extend(m.group(1).split())
        listens=[m.group(1).strip() for m in re.finditer(r"(?m)^\s*listen\s+([^;]+);",block_text)]
        if any(domain==n or domain in n for n in names):
            scheme="https" if any("443" in x or "ssl" in x.split() for x in listens) else "http"
            locations=[]; k=0; bl=[x[3] for x in block]
            while k<len(bl):
                if re.match(r"^\s*location\s+[^\{]+\{",strip_line(bl[k])):
                    loc_start=k; d=0; z=k
                    while z<len(bl):
                        c=strip_line(bl[z]); d+=c.count("{")-c.count("}")
                        if z>k and d<=0: break
                        z+=1
                    loc_text="\n".join(bl[loc_start:z+1]); first=strip_line(bl[k]).strip(); lm=re.match(r"location\s+(.+?)\s*\{",first); pattern=lm.group(1).strip() if lm else "unknown"
                    locations.append({"pattern":pattern,"proxy_pass":[m.group(1).strip() for m in re.finditer(r"(?m)^\s*proxy_pass\s+([^;]+);",loc_text)],"proxy_http_version":[m.group(1).strip() for m in re.finditer(r"(?m)^\s*proxy_http_version\s+([^;]+);",loc_text)],"proxy_set_header":[m.group(1).strip() for m in re.finditer(r"(?m)^\s*proxy_set_header\s+([^;]+);",loc_text) if any(x in m.group(1).lower() for x in ("upgrade","connection","host","origin"))],"proxy_read_timeout":[m.group(1).strip() for m in re.finditer(r"(?m)^\s*proxy_read_timeout\s+([^;]+);",loc_text)],"proxy_send_timeout":[m.group(1).strip() for m in re.finditer(r"(?m)^\s*proxy_send_timeout\s+([^;]+);",loc_text)],"auth_basic":bool(re.search(r"(?m)^\s*auth_basic\s+",loc_text))})
                    k=z
                k+=1
            servers.append({"order":len(servers)+1,"source_file":fn,"source_line":fl,"scheme":scheme,"server_names":names,"listen":listens,"locations":locations,"root_proxy_pass":[m.group(1).strip() for m in re.finditer(r"(?m)^\s*proxy_pass\s+([^;]+);",block_text)],"auth_basic":bool(re.search(r"(?m)^\s*auth_basic\s+",block_text)),"block":block_text})
        i=j
    i+=1
http=[s for s in servers if s["scheme"]=="http"]; https=[s for s in servers if s["scheme"]=="https"]
for group in (http,https):
    for pos,s in enumerate(group): s["effective_candidate"]=(pos==0); s["later_matching_candidate"]=(pos>0)
warn=[line for line in lines if re.search(r"(?i)(conflicting server name|ignored)",line)]
def route(server,target):
    if not server: return None
    for loc in server["locations"]:
        p=loc["pattern"].replace("= ","").strip()
        if p==target or (target=="/" and p in ("/","^~ /")): return loc
    return None
eff_http=http[0] if http else None; eff_https=https[0] if https else None
root=route(eff_https,"/") or route(eff_http,"/"); admin=route(eff_https,"/admin") or route(eff_http,"/admin")
payload={"nginx_test_output_present":bool(text.strip()),"configuration_load_order":files,"matching_server_blocks":servers,"effective_http_candidate":eff_http,"effective_https_candidate":eff_https,"current_root_route":root,"current_admin_route":admin,"duplicate_matching_blocks":max(0,len(servers)-len([x for x in (eff_http,eff_https) if x])),"conflict_or_ignored_warnings":warn,"interpretation":"The first matching block per HTTP/HTTPS load order is the effective candidate; address-specific listen precedence still requires review before mutation."}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY
python3 -m json.tool "$NGINX_JSON" >> "$RUN_LOG" 2>/dev/null || log "NGINX_ANALYSIS=FAILED"
EFFECTIVE_HTTP_CONFIG="$(json_get "$NGINX_JSON" effective_http_candidate.source_file)"
EFFECTIVE_HTTPS_CONFIG="$(json_get "$NGINX_JSON" effective_https_candidate.source_file)"
CURRENT_ROOT_UPSTREAM="$(json_get "$NGINX_JSON" current_root_route.proxy_pass.0)"
CURRENT_ADMIN_UPSTREAM="$(json_get "$NGINX_JSON" current_admin_route.proxy_pass.0)"
DUPLICATE_SERVER_BLOCKS="$(json_get "$NGINX_JSON" duplicate_matching_blocks)"
[ -n "$EFFECTIVE_HTTP_CONFIG" ] || EFFECTIVE_HTTP_CONFIG="not_found"
[ -n "$EFFECTIVE_HTTPS_CONFIG" ] || EFFECTIVE_HTTPS_CONFIG="not_found"
[ -n "$CURRENT_ROOT_UPSTREAM" ] || CURRENT_ROOT_UPSTREAM="not_found"
[ -n "$CURRENT_ADMIN_UPSTREAM" ] || CURRENT_ADMIN_UPSTREAM="not_found"
[ -n "$DUPLICATE_SERVER_BLOCKS" ] || DUPLICATE_SERVER_BLOCKS="unknown"

section "PUBLIC EDGE WITHOUT CREDENTIALS"
for target in "public_http|http://$DOMAIN/" "public_https|https://$DOMAIN/"; do
  name="${target%%|*}"; url="${target#*|}"; headers="$TMP_ROOT/$name.headers"
  code="$(curl -sS -k --max-time 10 -D "$headers" -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || true)"
  log "PUBLIC_HTTP_PROBE=$name status=${code:-000}"
  header_summary "$headers" | sanitize_stream >> "$RUN_LOG"
done

section "ACTIVE QUEUE READ ONLY"
python3 - "$ORIS_REPO/orchestration/dev_employee_queue" "$QUEUE_JSON" <<'PY'
import json, re, sys
from pathlib import Path
root=Path(sys.argv[1]); out=Path(sys.argv[2]); active=[]; seen=set()
patterns=("*.queued.json","*.running.json","*.claimed.json","*.planning.json","*.executing.json","*.committing.json","*.pushing.json","*.cancelling.json")
if root.exists():
    for pattern in patterns:
        for p in sorted(root.glob(pattern)):
            if p in seen: continue
            seen.add(p); task_id=re.sub(r"\.(queued|running|claimed|planning|executing|committing|pushing|cancelling)\.json$","",p.name); status="unknown"
            try:
                data=json.loads(p.read_text(encoding="utf-8")); status=str(data.get("canonical_status") or data.get("status") or status); task_id=str(data.get("task_id") or task_id)
            except Exception: pass
            active.append({"task_id":task_id,"status":status,"descriptor":p.name})
out.write_text(json.dumps({"active_count":len(active),"active":active},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY
python3 -m json.tool "$QUEUE_JSON" >> "$RUN_LOG" 2>/dev/null || log "QUEUE_SCAN=FAILED"
ACTIVE_QUEUE_COUNT="$(json_get "$QUEUE_JSON" active_count)"
[ -n "$ACTIVE_QUEUE_COUNT" ] || ACTIVE_QUEUE_COUNT="unknown"

section "REPOSITORY BASELINES READ ONLY"
python3 - "$ORIS_REPO" "$PRODUCT_REPO" "$EXPECTED_PRODUCT_COMMIT" "$BASELINE_JSON" <<'PY'
import json, subprocess, sys
from pathlib import Path
oris=Path(sys.argv[1]); product=Path(sys.argv[2]); expected=sys.argv[3]; out=Path(sys.argv[4])
def run(repo,*args):
    try:
        p=subprocess.run(["git","-C",str(repo),*args],text=True,capture_output=True,timeout=30); return p.returncode,p.stdout.strip(),p.stderr.strip()
    except Exception as e: return 99,"",type(e).__name__
def one(repo,label):
    if not (repo/".git").exists(): return {"label":label,"exists":False}
    _,head,_=run(repo,"rev-parse","HEAD"); _,branch,_=run(repo,"branch","--show-current"); _,remote,_=run(repo,"remote","get-url","origin")
    if "@" in remote and "://" in remote:
        prefix,rest=remote.split("://",1)
        if "@" in rest: remote=prefix+"://<redacted>@"+rest.split("@",1)[1]
    _,status,_=run(repo,"status","--porcelain","--untracked-files=all"); rc,ls,_=run(repo,"ls-remote","--heads","origin","refs/heads/main"); remote_main=ls.split()[0] if rc==0 and ls else ""
    return {"label":label,"exists":True,"path":str(repo),"head":head,"branch":branch,"remote":remote,"remote_main":remote_main,"clean":not bool(status),"status_entry_count":len(status.splitlines()) if status else 0}
payload={"oris":one(oris,"oris"),"product":one(product,"oris-final-acceptance-api"),"expected_product_commit":expected}
payload["product"]["head_matches_expected"]=payload["product"].get("head")==expected; payload["product"]["remote_matches_expected"]=payload["product"].get("remote_main")==expected
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY
python3 -m json.tool "$BASELINE_JSON" >> "$RUN_LOG" 2>/dev/null || log "BASELINE_SCAN=FAILED"
PRODUCT_HEAD="$(json_get "$BASELINE_JSON" product.head)"
PRODUCT_REMOTE_MAIN="$(json_get "$BASELINE_JSON" product.remote_main)"
PRODUCT_CLEAN="$(json_get "$BASELINE_JSON" product.clean)"
[ -n "$PRODUCT_HEAD" ] || PRODUCT_HEAD="not_found"
[ -n "$PRODUCT_REMOTE_MAIN" ] || PRODUCT_REMOTE_MAIN="not_found"
[ -n "$PRODUCT_CLEAN" ] || PRODUCT_CLEAN="unknown"

section "DISCOVERY DECISION"
CRITICAL_FAILURES=0
[ "$OPENCLAW_SERVICE_STATE" = "active" ] || CRITICAL_FAILURES=$((CRITICAL_FAILURES+1))
[ "$OPENCLAW_ROOT_STATUS" = "200" ] || CRITICAL_FAILURES=$((CRITICAL_FAILURES+1))
case "$NGINX_T_RESULT" in PASS|PASS_NON_SUDO) ;; *) CRITICAL_FAILURES=$((CRITICAL_FAILURES+1));; esac
[ "$INTAKE_LOOPBACK_ONLY" = "YES" ] || CRITICAL_FAILURES=$((CRITICAL_FAILURES+1))
if [ "$CRITICAL_FAILURES" -eq 0 ]; then
  RESULT="DIAGNOSED"; DISCOVERY_COMPLETE="YES"; FAILURE_CODE=""
  if [ "$ACTIVE_QUEUE_COUNT" = "0" ] && [ "$PRODUCT_CLEAN" = "YES" ]; then NEXT_ACTION="READ_GITHUB_EVIDENCE_AND_DESIGN_REVERSIBLE_MIGRATION"; else NEXT_ACTION="REVIEW_ACTIVE_QUEUE_OR_PRODUCT_BASELINE_BEFORE_MIGRATION"; fi
else
  RESULT="FAILED"; DISCOVERY_COMPLETE="PARTIAL"; FAILURE_CODE="critical_discovery_checks_failed"; NEXT_ACTION="READ_GITHUB_EVIDENCE_AND_REPAIR_DISCOVERY_BLOCKERS"
fi
log "RESULT=$RESULT"; log "DISCOVERY_COMPLETE=$DISCOVERY_COMPLETE"; log "FAILURE_CODE=$FAILURE_CODE"; log "CRITICAL_FAILURE_COUNT=$CRITICAL_FAILURES"; log "NEXT_ACTION=$NEXT_ACTION"

export TASK_ID STAMP RESULT FAILURE_CODE DISCOVERY_COMPLETE OPENCLAW_SCOPE OPENCLAW_SERVICE_STATE OPENCLAW_VERSION OPENCLAW_ROOT_STATUS SPA_FALLBACK WEBSOCKET_CANDIDATE_COUNT NGINX_T_RESULT EFFECTIVE_HTTP_CONFIG EFFECTIVE_HTTPS_CONFIG CURRENT_ROOT_UPSTREAM CURRENT_ADMIN_UPSTREAM DUPLICATE_SERVER_BLOCKS ACTIVE_QUEUE_COUNT PRODUCT_HEAD PRODUCT_REMOTE_MAIN PRODUCT_CLEAN INTAKE_LOOPBACK_ONLY NEXT_ACTION EVIDENCE_LOG_REL EVIDENCE_JSON_REL
python3 - "$RESULT_JSON" "$CONFIG_JSON" "$UI_JSON" "$NGINX_JSON" "$QUEUE_JSON" "$BASELINE_JSON" <<'PY'
import json, os, sys
from pathlib import Path
out=Path(sys.argv[1])
def load(path):
    try: return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception: return None
payload={"task_id":os.environ.get("TASK_ID"),"checked_at":os.environ.get("STAMP"),"result":os.environ.get("RESULT"),"discovery_complete":os.environ.get("DISCOVERY_COMPLETE"),"failure_code":os.environ.get("FAILURE_CODE"),"safety":{"configuration_or_service_changed":False,"product_task_submitted":False,"secret_values_recorded":False,"main_worktree_used_for_evidence_commit":False},"openclaw":{"scope":os.environ.get("OPENCLAW_SCOPE"),"service_state":os.environ.get("OPENCLAW_SERVICE_STATE"),"version":os.environ.get("OPENCLAW_VERSION"),"root_status":os.environ.get("OPENCLAW_ROOT_STATUS"),"spa_fallback":os.environ.get("SPA_FALLBACK"),"websocket_candidate_count":os.environ.get("WEBSOCKET_CANDIDATE_COUNT"),"config_key_discovery":load(sys.argv[2]),"ui_asset_signals":load(sys.argv[3])},"nginx":{"test":os.environ.get("NGINX_T_RESULT"),"effective_http_config":os.environ.get("EFFECTIVE_HTTP_CONFIG"),"effective_https_config":os.environ.get("EFFECTIVE_HTTPS_CONFIG"),"current_root_upstream":os.environ.get("CURRENT_ROOT_UPSTREAM"),"current_admin_upstream":os.environ.get("CURRENT_ADMIN_UPSTREAM"),"duplicate_matching_blocks":os.environ.get("DUPLICATE_SERVER_BLOCKS"),"analysis":load(sys.argv[4])},"queue":load(sys.argv[5]),"repositories":load(sys.argv[6]),"intake_loopback_only":os.environ.get("INTAKE_LOOPBACK_ONLY"),"evidence":{"log_path":os.environ.get("EVIDENCE_LOG_REL"),"json_path":os.environ.get("EVIDENCE_JSON_REL"),"self_commit_sha_omitted_to_prevent_post_commit_log_drift":True},"next_action":os.environ.get("NEXT_ACTION")}
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
PY

section "EVIDENCE SECRET SCAN"
if python3 - "$RUN_LOG" "$RESULT_JSON" <<'PY'
import re, sys
from pathlib import Path
bad=[]
patterns=[re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),re.compile(r"(?i)authorization\s*:\s*(?:bearer|basic)\s+(?!<redacted>)[A-Za-z0-9._~+/-]{12,}={0,2}"),re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),re.compile(r"(?i)\b(?:token|api[-_]?key|secret|password|credential|client[-_]?secret)\b\s*[:=]\s*(?!<redacted>|true\b|false\b|null\b|yes\b|no\b)[\"']?[A-Za-z0-9._~+/-]{16,}")]
for name in sys.argv[1:]:
    text=Path(name).read_text(encoding="utf-8",errors="replace")
    for p in patterns:
        if p.search(text): bad.append((name,p.pattern))
if bad: print("SECRET_SCAN_MATCH_COUNT="+str(len(bad))); raise SystemExit(1)
print("SECRET_SCAN_MATCH_COUNT=0")
PY
then
  SECRET_SCAN="PASS"; log "SECRET_SCAN=PASS"
else
  SECRET_SCAN="FAILED"; RESULT="FAILED"; FAILURE_CODE="evidence_secret_scan_failed"; DISCOVERY_COMPLETE="NO"; NEXT_ACTION="REPAIR_REDACTION_BEFORE_COMMIT"; final_summary; exit 1
fi

section "DETACHED WORKTREE EVIDENCE COMMIT"
if ! git -C "$ORIS_REPO" fetch origin main >> "$RUN_LOG" 2>&1; then fail_now "oris_fetch_failed_before_evidence" "REPAIR_GITHUB_CONNECTIVITY"; fi
if ! git -C "$ORIS_REPO" worktree add --detach "$WORKTREE" origin/main >> "$RUN_LOG" 2>&1; then fail_now "detached_worktree_create_failed" "INSPECT_ORIS_WORKTREE_STATE"; fi
mkdir -p "$WORKTREE/$EVIDENCE_DIR_REL"
cp "$RUN_LOG" "$WORKTREE/$EVIDENCE_LOG_REL"
cp "$RESULT_JSON" "$WORKTREE/$EVIDENCE_JSON_REL"
if ! git -C "$WORKTREE" add -- "$EVIDENCE_LOG_REL" "$EVIDENCE_JSON_REL"; then fail_now "evidence_git_add_failed" "INSPECT_DETACHED_WORKTREE"; fi
if ! git -C "$WORKTREE" diff --cached --check >/dev/null 2>&1; then fail_now "evidence_diff_check_failed" "REPAIR_EVIDENCE_FORMAT"; fi
if ! git -C "$WORKTREE" commit -m "chore(dev-employee): record native OpenClaw UI discovery $STAMP" >/dev/null 2>&1; then fail_now "evidence_commit_failed" "INSPECT_GIT_IDENTITY_AND_WORKTREE"; fi
if ! git -C "$WORKTREE" fetch origin main >/dev/null 2>&1; then fail_now "evidence_refetch_failed" "REPAIR_GITHUB_CONNECTIVITY"; fi
if [ "$(git -C "$WORKTREE" merge-base HEAD origin/main 2>/dev/null)" != "$(git -C "$WORKTREE" rev-parse origin/main 2>/dev/null)" ]; then
  if ! git -C "$WORKTREE" rebase origin/main >/dev/null 2>&1; then fail_now "evidence_rebase_failed" "INSPECT_CONCURRENT_ORIS_UPDATE"; fi
fi
EVIDENCE_COMMIT="$(git -C "$WORKTREE" rev-parse HEAD 2>/dev/null || true)"
if ! git -C "$WORKTREE" push origin HEAD:main >/dev/null 2>&1; then fail_now "evidence_push_failed" "INSPECT_ORIS_MAIN_PUSH"; fi
REMOTE_MAIN="$(git -C "$WORKTREE" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
if [ -n "$EVIDENCE_COMMIT" ] && [ "$REMOTE_MAIN" = "$EVIDENCE_COMMIT" ]; then EVIDENCE_REMOTE_VERIFIED="YES"; else EVIDENCE_REMOTE_VERIFIED="NO"; RESULT="FAILED"; FAILURE_CODE="evidence_remote_sha_mismatch"; NEXT_ACTION="VERIFY_ORIS_REMOTE_MAIN"; fi

final_summary
[ "$RESULT" = "FAILED" ] && exit 1
exit 0
