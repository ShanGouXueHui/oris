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

## Versioned endpoints

### GET /v1/health
No application bearer required.
Returns:
{
  "ok": true,
  "request_id": null,
  "data": {
    "service": "oris-http-api",
    "version": "v1",
    "listen": "http://127.0.0.1:8788"
  },
  "error": null
}

### GET /v1/runtime/plan
Requires application bearer token.

### POST /v1/infer
Requires application bearer token.

Request:
{
  "role": "free_fallback | primary_general | report_generation | coding | cn_candidate_pool",
  "prompt": "string",
  "request_id": "optional string",
  "source": "optional string",
  "show_raw": false
}

Success response:
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

Failure response:
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

## Legacy compatibility endpoints
The following endpoints are still kept for backward compatibility:
- /health
- /runtime/plan
- /infer
