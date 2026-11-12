# API execution

```bash
ghl hub operations "contact"
ghl hub operations --domain affiliate-manager
ghl hub schema contacts:upsert-contact
ghl hub call workflows:get-workflow --query '{"locationId":"LOCATION"}'
ghl hub call workflows:get-workflow --query '{"locationId":"LOCATION"}' --execute
```

Operation IDs are namespaced `DOMAIN:operationId`. Search first; do not guess an ID.
`schema` includes the original security requirements and component schemas. The
source JSON is in `knowledge/upstream/apps`. Versioned specs are separately namespaced as `v3/DOMAIN:operationId`. For example,
use `--domain v3/chat-widget` to discover that surface. Each operation retains its
documented Version header; do not treat v3 and v2 as the same contract.

Supply path/query arguments as JSON objects with the schema's actual field types.
Supply a body as inline JSON or `--body @/absolute/payload.json`. The builder fills
a configured location only into documented path/query `locationId` parameters.
It does not invent body defaults. Prepare a request before sending a mutation.
`--execute` sends the request; without it there is no network call. MCP `ghl_call`
uses the same shape with `execute: true` to send.

Validation checks required fields, basic JSON types, enums, array elements, object
properties, local/external refs and allOf. It is not a complete OpenAPI validator:
oneOf/anyOf, formats, ranges and business constraints still need schema inspection
and provider validation. Multipart uploads use `--files` with a JSON object mapping field names to local
paths (or lists of paths) and `--body` for the form fields. Inspect the schema for
the exact file-field names; files must exist on the machine running the CLI/MCP.
OAuth code/refresh grants require their documented form request and credentials;
the CLI is not a secure token lifecycle service.

Every request stays on services.leadconnectorhq.com and refuses redirects. GET/HEAD
retry bounded transient HTTP failures; POST/PUT/PATCH/DELETE do not replay. A write
can succeed even if the response is lost; read before retrying. The result is one
page: use that operation's cursor or offset fields when processing large collections.

401: wrong/expired token; 403: scopes, installation type or role; 404: wrong resource,
location or path; 422: inspect the documented body; 429: quota. If a read works and a
write fails, inspect the write scope rather than replacing the token blindly.
For a destructive or externally visible action use the user's task scope to determine
whether execution is authorized; the dry-run flag is a planning mechanism, not approval.
