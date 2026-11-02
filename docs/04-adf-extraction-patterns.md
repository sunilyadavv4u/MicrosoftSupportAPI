# ADF Extraction Patterns — Normal, Pagination, Incremental, Errors

## 1. Normal single-request extraction

Use for a small source or a deliberately unpaged API test.

Example:
`GET /api/apikey/labor-rate-exception?pagination=none`

Caution: `pagination=none` is capped by the API's configured maximum page size (default 1000); it is not intended to return an unbounded 640k dataset. Use pagination for large resources.

## 2. Page-number pagination (ADF REST Copy Activity)

Request:
`GET /api/apikey/timesheet-entry?page=1&page_size=1000`

Envelope contains:
```json
{
  "data": [],
  "next": "https://api-host/api/apikey/timesheet-entry?page=2&page_size=1000"
}
```

ADF Copy Activity → Source → Pagination rules:
```json
{
  "AbsoluteUrl": "$.next",
  "MaxRequestNumber": "10000"
}
```

The API returns `next: null` on the last page, so ADF stops. Use response format `envelope` (default). ADF REST connector does not support pagination when the response is a top-level JSON array.

## 3. OData-style nextLink pagination

Request:
`GET /api/apikey/timesheet-entry?page=1&page_size=1000&response_format=odata`

Response:
```json
{
  "@odata.count": 640000,
  "value": [],
  "@odata.nextLink": "https://api-host/api/apikey/timesheet-entry?page=2&page_size=1000&response_format=odata"
}
```

ADF Copy Activity pagination rule:
```json
{
  "AbsoluteUrl": "$['@odata.nextLink']",
  "MaxRequestNumber": "10000"
}
```

## 4. Offset / limit pagination

Request:
`GET /api/apikey/timesheet-entry?pagination=offset&offset=0&limit=1000`

Next link uses the next offset. For ADF use:
```json
{
  "AbsoluteUrl": "$.next",
  "MaxRequestNumber": "10000"
}
```

## 5. Fixed RANGE pagination (when API accepts offset)

The REST connector supports RANGE rules. For an API that takes `offset` and `limit`, a fixed range could be configured:
```json
{
  "QueryParameters.offset": "RANGE:0:639000:1000"
}
```
For the final request ensure the API and range semantics include all rows. The API's dynamic `next` link approach is safer for this project because it stops based on the actual response.

## 6. ADF REST linked service / dataset

Linked service:
- Type: REST
- Base URL: `https://<API-HOST>` (cloud) or `http://<SHIR-HOST>:8000` (local)
- Authentication: choose the appropriate auth mode from `03-authentication-and-spn.md`.

REST dataset:
- Relative URL: `/api/apikey/timesheet-entry?page=1&page_size=1000`
- Request method: GET

Copy Activity source:
- Pagination rules as above.
- Request timeout: increase for larger pages if needed.
- Request interval: optionally set e.g. 00:00:01 to avoid aggressive requests.

Sink can be Azure SQL Database, ADLS Gen2, Blob Storage, or Fabric Lakehouse depending on the linked service and integration runtime.

## 7. Nested JSON and array response scenarios

- Default `envelope` response: array is under `data`.
- `odata` response: array is under `value`.
- `array` response: top-level array; useful for simple clients, but ADF REST pagination is unsupported for top-level array responses.
- In Copy Activity mapping, import schema and map the returned collection. If the connector imports the wrapper object rather than rows, configure collection reference / mapping against `data` or `value` according to the source mapping UI.

## 8. Incremental extraction / watermark

Only `labor-transaction` has `LastModifiedTimestamp`.

Example:
`GET /api/apikey/labor-transaction?modified_since=2024-05-07%2000:00:00&page=1&page_size=500`

ADF pattern:
1. Lookup the last successful watermark from a control table.
2. Set pipeline parameter `p_watermark`.
3. Call the REST endpoint with `modified_since=@{pipeline().parameters.p_watermark}`.
4. Copy data to staging.
5. On successful load, update watermark to the maximum `LastModifiedTimestamp` processed.
6. On failure, do not advance the watermark.

This supplied CSV is a static snapshot; it tests watermark filtering but does not generate new updates automatically.

## 9. Filtering and query parameters

Examples:
```text
/api/apikey/labor-transaction?vendor_code=VEN-IMPT&activity_type=Repro
/api/apikey/timesheet-entry?employee_email=user@example.com&submission_status=Approved
/api/apikey/kb-article?product_code=M365-TEAMS&status=Published
/api/apikey/kb-article-view?article_code=KB0000001&date_from=2023-01-01&date_to=2023-12-31
```
A filter only applies when that column exists in the selected source. Unsupported filters are ignored.

## 10. Retry, timeout, and failure branches

All error endpoints require the API key header:
- `/api/errors/400`
- `/api/errors/401`
- `/api/errors/403`
- `/api/errors/404`
- `/api/errors/408`
- `/api/errors/429` (also returns `Retry-After: 15`)
- `/api/errors/500`
- `/api/errors/502`
- `/api/errors/503`
- `/api/errors/504`

Delay:
`GET /api/delay/20` waits 20 seconds.

ADF exercises:
- Set Copy Activity retry count and retry interval.
- Use Web Activity / If Condition to branch on failure.
- Test 429 retry and inspect retry-after behavior.
- Test timeout by setting a request timeout below the simulated delay.
- Route failures to a notification activity / error log table.
- Use an Execute Pipeline activity for a reusable error-handling child pipeline.

## 11. POST, PUT, PATCH, DELETE tests

The `/write-test` endpoints operate on a disposable API test table only; they do not mutate source CSV tables.

POST:
```json
{
  "resource": "labor-api-test",
  "data": {"run_id": "ADF-001", "status": "created"}
}
```

Then GET `/api/apikey/write-test/{id}`, PUT/PATCH and DELETE the record. These routes let you test ADF Web Activity and REST sink methods. The REST connector supports GET/POST for source and POST/PUT/PATCH for sink; DELETE can be tested through Web Activity.

## 12. Large data extraction recommendations

For 640,000 timesheet rows:
- Begin with page_size 500 or 1000.
- Avoid requesting all records in one response.
- Test 429 and 500 handling before long-running extraction.
- Use a stable ordering (the API defaults to source row order; use `order_by` when a stable business key exists).
- Persist watermarks only after a successful sink commit.
- For production APIs, prefer a server-issued opaque continuation token rather than exposing raw offset if the source data can change during paging.
