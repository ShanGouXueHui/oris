# Marker and pre-install backup validation. Only booleans and non-secret metadata are promoted.
python3 - "$MARKER_FILE" "$EXPECTED_BACKUP" "$EXPECTED_PLUGIN_SOURCE_COMMIT" "$EXPECTED_ARTIFACT_SHA256" "$PLUGIN_ID" "$PLUGIN_VERSION" "$TOOL_1" "$TOOL_2" "$TOOL_3" "$TMP_ROOT/marker-safe.json" <<'PY_MARKER'
import json, os, re, sys
from pathlib import Path
marker, expected_backup, source_commit, artifact, plugin_id, version, *rest = sys.argv[1:]
expected_tools = set(rest[:3]); output = Path(rest[3])
marker_path=Path(marker); backup_path=Path(expected_backup)
payload={
 'marker_exists':marker_path.is_file(),
 'marker_owner_ok':False,
 'marker_mode_ok':False,
 'marker_json_ok':False,
 'marker_state_ok':False,
 'marker_plugin_ok':False,
 'marker_version_ok':False,
 'marker_source_commit_ok':False,
 'marker_artifact_ok':False,
 'marker_tools_ok':False,
 'marker_backup_reference_ok':False,
 'backup_exists':backup_path.is_file(),
 'backup_owner_ok':False,
 'backup_mode_ok':False,
 'backup_json_ok':False,
 'secret_values_recorded':False,
}
try:
 st=marker_path.stat(); payload['marker_owner_ok']=st.st_uid==os.getuid(); payload['marker_mode_ok']=(st.st_mode & 0o777)==0o600
 data=json.loads(marker_path.read_text(encoding='utf-8')); payload['marker_json_ok']=isinstance(data,dict)
 if isinstance(data,dict):
  payload['marker_state_ok']=data.get('state')=='installed_tools_denied'
  payload['marker_plugin_ok']=data.get('plugin_id')==plugin_id
  payload['marker_version_ok']=data.get('plugin_version')==version
  payload['marker_source_commit_ok']=data.get('source_commit')==source_commit
  payload['marker_artifact_ok']=data.get('artifact_sha256')==artifact
  payload['marker_tools_ok']=set(data.get('denied_tools') or [])==expected_tools
  try: payload['marker_backup_reference_ok']=Path(str(data.get('config_backup') or '')).resolve()==backup_path.resolve()
  except Exception: pass
except Exception:
 pass
try:
 st=backup_path.stat(); payload['backup_owner_ok']=st.st_uid==os.getuid(); payload['backup_mode_ok']=(st.st_mode & 0o777)==0o600
 data=json.loads(backup_path.read_text(encoding='utf-8')); payload['backup_json_ok']=isinstance(data,dict)
except Exception:
 pass
output.write_text(json.dumps(payload,sort_keys=True,indent=2)+'\n',encoding='utf-8')
PY_MARKER
if [ "$?" -ne 0 ]; then
  record_check "install_marker_and_backup" "FAIL" "safe_marker_parser_failed"
else
  MARKER_READY="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print("YES" if all(v is True for k,v in d.items() if k not in {"secret_values_recorded"}) else "NO")' "$TMP_ROOT/marker-safe.json" 2>/dev/null || echo NO)"
  if [ "$MARKER_READY" = "YES" ]; then record_check "install_marker_and_backup" "PASS" "marker_and_backup_contract_match"; else record_check "install_marker_and_backup" "FAIL" "marker_or_backup_contract_mismatch"; fi
fi

