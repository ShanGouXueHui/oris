# ORIS API Contract

## External HTTPS base
https://control.orisfy.com/oris-api

## Authentication
Two layers are currently applied:
1. Nginx Basic Auth
2. Application-level Bearer token

Bearer token can be sent with:
- Authorization: Bearer <token>
or
- X-ORIS-API-Key: <token>

## Stable endpoints

### GET /v1/health
No application bearer required.

### GET /v1/runtime/plan
Requires application bearer token.

### POST /v1/infer
Requires application bearer token.

## POST /v1/infer request
{
  "role": "free_fallback | primary_general | report_generation | coding | cn_candidate_pool",
  "prompt": "string",
  "request_id": "optional string",
  "source": "optional string",
  "show_raw": false
}

## Success response
{
  "ok": true,
  "request_id": "string",
  "data": {
    "role": "string",
    "selected_model": "string",
    "execution_primary": "string",
    "used_provider": "string",
    "used_model": "string",
    "attempt": 1,
    "text": "string",
    "attempts_log": [],
    "source": "string"
  },
  "error": null
}

## Failure response
{
  "ok": false,
  "request_id": "string",
  "data": null,
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}

## Notes
This is a new system.
Legacy non-versioned endpoints are intentionally removed from the stable external contract.
