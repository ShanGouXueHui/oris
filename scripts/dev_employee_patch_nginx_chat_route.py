#!/usr/bin/env python3
"""Structurally patch the effective ORIS Nginx vhost for chat POST.

The patcher is deterministic and idempotent. Existing location-level read-only
method guards are preserved. A server-level method guard is replaced only when
one actually exists. The only new write route is the exact authenticated chat
endpoint. Credential values are never read or emitted.
"""

import argparse
import json
import re
from pathlib import Path

MAP_MARKER = "# ORIS_CHAT_WRITE_POLICY_BEGIN"
MAP_BLOCK = '''# ORIS_CHAT_WRITE_POLICY_BEGIN
map "$request_method:$uri" $oris_readonly_request_blocked {
    default 1;
    ~^(GET|HEAD): 0;
    "POST:/api/chat/messages" 0;
}
# ORIS_CHAT_WRITE_POLICY_END

'''
CHAT_MARKER = "# ORIS_CHAT_MESSAGES_BEGIN"


def matching_brace(text, open_index):
    depth = 0
    quote = None
    escaped = False
    comment = False
    for index in range(open_index, len(text)):
        char = text[index]
        if comment:
            if char == "\n":
                comment = False
            continue
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char == "#":
            comment = True
            continue
        if char in ('"', "'"):
            quote = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unbalanced Nginx block")


def directive_blocks(text, directive):
    pattern = re.compile(r"(?m)^[ \t]*" + re.escape(directive) + r"\b[^\n{]*\{")
    result = []
    for match in pattern.finditer(text):
        open_index = text.find("{", match.start(), match.end())
        close_index = matching_brace(text, open_index)
        result.append((match.start(), close_index + 1, text[match.start() : close_index + 1]))
    return result


def effective_https_server(text):
    matches = []
    for start, end, block in directive_blocks(text, "server"):
        if not re.search(r"\bserver_name\b[^;]*\bcontrol\.orisfy\.com\b", block):
            continue
        if not re.search(r"(?m)^[ \t]*listen[ \t]+[^;\n]*\b443\b", block):
            continue
        matches.append((start, end, block))
    if len(matches) != 1:
        raise ValueError("effective HTTPS server count=%d" % len(matches))
    return matches[0]


def classify_method_guards(block):
    locations = directive_blocks(block, "location")
    server_level = []
    location_level = []
    for start, end, candidate in directive_blocks(block, "if"):
        if "$request_method" not in candidate or not re.search(r"\breturn\s+403\s*;", candidate):
            continue
        inside_location = any(
            location_start < start and end <= location_end
            for location_start, location_end, _ in locations
        )
        if inside_location:
            location_level.append((start, end, candidate))
        else:
            server_level.append((start, end, candidate))
    return server_level, location_level


def patch_config(text):
    changed = False
    start, end, block = effective_https_server(text)
    server_guards, location_guards = classify_method_guards(block)

    if MAP_MARKER not in text:
        if len(server_guards) > 1:
            raise ValueError("server-level request-method deny block count=%d" % len(server_guards))
        if len(server_guards) == 1:
            guard_start, guard_end, guard = server_guards[0]
            indent_match = re.match(r"([ \t]*)", guard)
            indent = indent_match.group(1) if indent_match else "    "
            replacement = (
                indent
                + "if ($oris_readonly_request_blocked) {\n"
                + indent
                + "    return 403;\n"
                + indent
                + "}"
            )
            block = block[:guard_start] + replacement + block[guard_end:]
            text = MAP_BLOCK + text[:start] + block + text[end:]
            changed = True
    else:
        if "$oris_readonly_request_blocked" not in block:
            raise ValueError("map marker exists but effective server does not use it")

    start, end, block = effective_https_server(text)
    exact_location = bool(
        re.search(r"(?m)^[ \t]*location[ \t]+=[ \t]*/api/chat/messages[ \t]*\{", block)
    )
    if not exact_location:
        server_indent_match = re.match(r"([ \t]*)server\b", block)
        server_indent = server_indent_match.group(1) if server_indent_match else ""
        indent = server_indent + "    "
        snippet = (
            "\n"
            + indent
            + CHAT_MARKER
            + "\n"
            + indent
            + "location = /api/chat/messages {\n"
            + indent
            + "    proxy_pass http://127.0.0.1:18893;\n"
            + indent
            + "    proxy_http_version 1.1;\n"
            + indent
            + "    proxy_pass_request_headers on;\n"
            + indent
            + "    proxy_set_header Host $host;\n"
            + indent
            + "    proxy_set_header X-Real-IP $remote_addr;\n"
            + indent
            + "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
            + indent
            + "    proxy_set_header X-Forwarded-Proto $scheme;\n"
            + indent
            + "    proxy_set_header X-Forwarded-User $remote_user;\n"
            + indent
            + "    proxy_set_header X-ORIS-Chat-CSRF $http_x_oris_chat_csrf;\n"
            + indent
            + "    client_max_body_size 64k;\n"
            + indent
            + "    proxy_connect_timeout 10s;\n"
            + indent
            + "    proxy_read_timeout 120s;\n"
            + indent
            + "}\n"
            + indent
            + "# ORIS_CHAT_MESSAGES_END\n"
        )
        block = block[:-1] + snippet + block[-1:]
        text = text[:start] + block + text[end:]
        changed = True

    _, _, final_block = effective_https_server(text)
    final_server_guards, final_location_guards = classify_method_guards(final_block)
    map_guard_present = "$oris_readonly_request_blocked" in final_block
    server_guard_safe = len(final_server_guards) == 0 and (
        len(server_guards) == 0 or map_guard_present
    )
    audit = {
        "result": "PASS",
        "changed": changed,
        "map_policy_present": MAP_MARKER in text,
        "effective_guard_present": map_guard_present,
        "server_guard_safe": server_guard_safe,
        "server_method_guard_count_before": len(server_guards),
        "location_method_guard_count_before": len(location_guards),
        "location_method_guard_count_after": len(final_location_guards),
        "exact_chat_location_present": bool(
            re.search(r"(?m)^[ \t]*location[ \t]+=[ \t]*/api/chat/messages[ \t]*\{", final_block)
        ),
        "allowed_write_route": "POST:/api/chat/messages",
        "other_write_routes_allowed": False,
        "secret_values_recorded": False,
    }
    if not all(
        [
            audit["server_guard_safe"],
            audit["exact_chat_location_present"],
            audit["location_method_guard_count_after"] == audit["location_method_guard_count_before"],
        ]
    ):
        raise ValueError("post-patch contract failed")
    return text, audit


def self_test():
    fixtures = [
        '''server {
    listen 443 ssl;
    server_name control.orisfy.com;
    if ($request_method !~ ^(GET|HEAD)$) { return 403; }
    location / { proxy_pass http://127.0.0.1:18893; }
}
''',
        '''server {
  listen 443 ssl http2;
  server_name control.orisfy.com;
  if ($request_method !~* "^(GET|HEAD)$") {
      return 403;
  }
  location / {
      proxy_pass http://127.0.0.1:18893;
  }
}
''',
        '''server {
  listen 443 ssl;
  server_name control.orisfy.com;
  location = /api/projects {
      if ($request_method !~ ^(GET|HEAD)$) { return 403; }
      proxy_pass http://127.0.0.1:18893;
  }
  location = /api/goals {
      if ($request_method !~ ^(GET|HEAD)$) { return 403; }
      proxy_pass http://127.0.0.1:18893;
  }
  location / {
      if ($request_method !~ ^(GET|HEAD)$) { return 403; }
      proxy_pass http://127.0.0.1:18893;
  }
}
''',
    ]
    for fixture in fixtures:
        patched, audit = patch_config(fixture)
        assert audit["result"] == "PASS"
        assert audit["server_guard_safe"] is True
        assert "location = /api/chat/messages" in patched
        assert audit["location_method_guard_count_after"] == audit["location_method_guard_count_before"]
        second, second_audit = patch_config(patched)
        assert second == patched
        assert second_audit["changed"] is False
    print(json.dumps({"result": "PASS", "fixtures": len(fixtures), "idempotent": True}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--audit")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.input or not args.output or not args.audit:
        parser.error("--input, --output and --audit are required")
    source = Path(args.input)
    patched, audit = patch_config(source.read_text(encoding="utf-8"))
    Path(args.output).write_text(patched, encoding="utf-8")
    Path(args.audit).write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
