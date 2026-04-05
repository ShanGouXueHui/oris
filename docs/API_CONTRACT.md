# ORIS API Contract

## External HTTPS base
https://control.orisfy.com/oris-api

## External authentication
External HTTPS access currently uses two layers:

1. Nginx Basic Auth
2. Application-level API key

Recommended external header usage:
- Basic Auth: handled by the HTTPS client
- Application API key: use `X-ORIS-API-Key: <token>`

For the current external HTTPS entrypoint, do not rely on `Authorization: Bearer <token>` together with Basic Auth in the same request, because the authorization header can conflict with the proxy auth layer.

## Stable endpoints

### GET /v1/health
External auth required:
- Basic Auth only

### GET /v1/runtime/plan
External auth required:
- Basic Auth
- X-ORIS-API-Key

### POST /v1/infer
External auth required:
- Basic Auth
- X-ORIS-API-Key

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
The stable external contract is versioned and v1-only.
