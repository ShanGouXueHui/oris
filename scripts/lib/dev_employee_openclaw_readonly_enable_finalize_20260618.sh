QUEUE_FINGERPRINT_AFTER="$(queue_fingerprint)"
ACTIVE_QUEUE_AFTER="$(active_queue_count)"
if [ "$QUEUE_FINGERPRINT_BEFORE" = "$QUEUE_FINGERPRINT_AFTER" ] && [ "$ACTIVE_QUEUE_AFTER" = "0" ]; then QUEUE_UNCHANGED="YES"; record_check "final_queue_invariant" "PASS" "fingerprint_unchanged_zero_active"; else fatal "queue_changed_during_browser_acceptance" "RESTORE_TOOLS_DENIED_AND_INSPECT_QUEUE"; fi

PRODUCT_HEAD_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD 2>/dev/null || true)"
PRODUCT_REMOTE_AFTER="$(git -C "$PRODUCT_REPO" ls-remote --heads origin refs/heads/main 2>/dev/null | awk '{print $1}')"
PRODUCT_STATUS_AFTER_FILE="$TMP_ROOT/product-status-after.bin"
git -C "$PRODUCT_REPO" status --porcelain=v1 -z --untracked-files=all > "$PRODUCT_STATUS_AFTER_FILE" || fatal "product_status_recapture_failed" "INSPECT_PRODUCT_REPOSITORY"
PRODUCT_STATUS_SHA_AFTER="$(sha256sum "$PRODUCT_STATUS_AFTER_FILE" | awk '{print $1}')"
PRODUCT_TREE_AFTER="$(git -C "$PRODUCT_REPO" rev-parse HEAD^{tree} 2>/dev/null || true)"
if [ "$PRODUCT_HEAD_BEFORE" = "$PRODUCT_HEAD_AFTER" ] && [ "$PRODUCT_REMOTE_BEFORE" = "$PRODUCT_REMOTE_AFTER" ] && [ "$PRODUCT_STATUS_SHA_BEFORE" = "$PRODUCT_STATUS_SHA_AFTER" ] && [ "$PRODUCT_TREE_BEFORE" = "$PRODUCT_TREE_AFTER" ]; then PRODUCT_UNCHANGED="YES"; record_check "final_product_invariant" "PASS" "head_remote_status_tree_unchanged"; else fatal "product_repository_changed_during_enablement" "RESTORE_TOOLS_DENIED_AND_PRODUCT_BASELINE"; fi

validate_config_scope "$SELECTED_POLICY_MODE" || fatal "final_config_scope_invalid" "RESTORE_TOOLS_DENIED"
CONFIG_SCOPE_VALID="YES"
record_check "final_config_scope" "PASS" "only_tools_allow_and_deny_changed"
inspect_runtime_safe || fatal "final_plugin_runtime_contract_failed" "RESTORE_TOOLS_DENIED"
WRITE_TOOLS_ABSENT="YES"
record_check "final_runtime_contract" "PASS" "three_readonly_tools_three_hooks_zero_write_tools"
verify_public_and_restricted_routes || fatal "final_public_or_restricted_route_contract_failed" "RESTORE_TOOLS_DENIED"
record_check "final_public_route_contract" "PASS" "public_root_matches_gateway_and_restricted_routes_remain_restricted"

[ "$(loopback_only "$ENQUEUE_PORT")" = "YES" ] || fatal "enqueue_listener_exposure_changed" "RESTORE_TOOLS_DENIED"
[ "$(loopback_only "$INTAKE_PORT")" = "YES" ] || fatal "intake_listener_exposure_changed" "RESTORE_TOOLS_DENIED"
record_check "final_private_listener_invariant" "PASS" "18891_and_18892_loopback_only"

ORIS_HEAD_AFTER="$(git -C "$ORIS_REPO" rev-parse HEAD 2>/dev/null || true)"
ORIS_STATUS_AFTER_FILE="$TMP_ROOT/oris-status-after.bin"
git -C "$ORIS_REPO" status --porcelain=v1 -z --untracked-files=all > "$ORIS_STATUS_AFTER_FILE" || fatal "oris_status_recapture_failed" "INSPECT_ORIS_REPOSITORY"
ORIS_STATUS_SHA_AFTER="$(sha256sum "$ORIS_STATUS_AFTER_FILE" | awk '{print $1}')"
[ "$ORIS_HEAD_BEFORE" = "$ORIS_HEAD_AFTER" ] && [ "$ORIS_STATUS_SHA_BEFORE" = "$ORIS_STATUS_SHA_AFTER" ] || fatal "oris_primary_worktree_changed" "RESTORE_TOOLS_DENIED_AND_INSPECT_WORKTREE"
record_check "oris_primary_worktree_invariant" "PASS" "head_and_status_unchanged_before_evidence_commit"

python3 - "$MARKER_FILE" "$SELECTED_POLICY_MODE" "$CONFIG_BACKUP_FILE" "$STAMP" <<'PY'
import json,os,sys
from pathlib import Path
path=Path(sys.argv[1]); data=json.loads(path.read_text(encoding='utf-8'))
data['state']='installed_readonly_tools_enabled'
data['readonly_enablement']={'policy_mode':sys.argv[2],'tools_denied_backup':sys.argv[3],'enabled_at':sys.argv[4],'write_tools_present':False,'browser_acceptance':True,'telemetry_privacy_pass':True}
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.chmod(path,0o600)
PY
[ "$?" -eq 0 ] || fatal "private_marker_finalize_failed" "RESTORE_TOOLS_DENIED"
record_check "private_marker_finalized" "PASS" "readonly_enabled_state_recorded_privately"

python3 - "$TMP_ROOT/direct-$SELECTED_POLICY_MODE.json" "$TMP_ROOT/browser-telemetry-safe.json" "$FINAL_DETAILS_JSON" <<'PY'
import json,sys
from pathlib import Path
direct=json.loads(Path(sys.argv[1]).read_text()); telemetry=json.loads(Path(sys.argv[2]).read_text())
payload={
 'direct_invocation':direct,
 'browser_telemetry':telemetry,
 'ttft_note':'TTFT is unavailable from the approved hook set; no synthetic TTFT value was fabricated.',
 'browser_surface':'OpenClaw native Control UI / native session',
 'product_task_submitted':False,
 'secret_values_recorded':False,
 'conversation_content_recorded':False,
}
Path(sys.argv[3]).write_text(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
PY
[ "$?" -eq 0 ] || fatal "final_details_build_failed" "RESTORE_TOOLS_DENIED"

RESULT="ENABLED_READONLY_ACCEPTED"
FAILURE_CODE=""
NEXT_ACTION="PERSIST_COMPLETION_AND_BEGIN_P1_TYPED_WRITE_ACTION_DESIGN"
ROLLBACK_HEALTHY="NOT_REQUIRED"
log "result=$RESULT"
log "selected_policy_mode=$SELECTED_POLICY_MODE"
log "direct_tool_calls_pass=YES"
log "browser_acceptance_pass=YES"
log "telemetry_privacy_pass=YES"
log "queue_unchanged=YES"
log "product_unchanged=YES"
log "write_tools_absent=YES"
log "product_task_submitted=NO"
log "secret_values_recorded=NO"

commit_evidence || fatal "enablement_evidence_commit_failed" "RESTORE_TOOLS_DENIED_AND_REPAIR_GITHUB_PUSH"
MUTATION_STARTED="NO"
summary
exit 0
