# End-to-end ADF test plan

## Connectivity first

### Local (Self-hosted IR)
- Install Self-hosted Integration Runtime on the same Windows host as this API.
- Start `start_local.bat`.
- ADF REST linked service base URL: `http://localhost:8000`.
- If SHIR is on a different host, use the API machine's private IP/DNS, not localhost, and allow inbound TCP 8000 in Windows Firewall.
- Azure Integration Runtime cannot use your laptop's localhost.

### Cloud
- Deploy the Docker image to a public HTTPS host.
- ADF Azure Integration Runtime uses `https://<host>`.
- Do not expose demo credentials. Configure Entra or strong secrets.

## Test cases

| # | Scenario | API / ADF action | Expected |
|---:|---|---|---|
| 1 | Health | Web GET `/health` | 200, 8 source counts |
| 2 | Metadata discovery | Web GET `/api/metadata` | All resources and columns |
| 3 | API Key | Copy `/api/apikey/labor-transaction` | 200 |
| 4 | Missing API Key | Same route without key | 401 |
| 5 | Invalid API Key | Wrong `x-api-key` | 401 |
| 6 | Basic Auth | Copy `/api/basic/timesheet-entry` | 200 |
| 7 | Invalid Basic | Wrong password | 401 |
| 8 | Static Bearer | Copy `/api/bearer/kb-article` | 200 |
| 9 | Local OAuth token | Web POST `/oauth/token` | JWT returned |
| 10 | Local OAuth resource | Copy `/api/oauth/kb-article-view` with token | 200 |
| 11 | Entra SPN | ADF Service Principal token to `/api/entra/...` | 200 when app role/audience/issuer correct |
| 12 | Page pagination | `page=1&page_size=500` + nextLink rule | All pages fetched |
| 13 | Offset pagination | `pagination=offset&offset=0&limit=500` | Offset advances |
| 14 | OData pagination | `response_format=odata` + `@odata.nextLink` | All pages fetched |
| 15 | Plain array | `response_format=array` | Array response; no REST connector pagination |
| 16 | Filtering | `vendor_code=VEN-IMPT` | Filtered rows |
| 17 | Date range | `date_from` / `date_to` | Date-filtered rows |
| 18 | Incremental | `labor-transaction?modified_since=...` | Watermark filtered rows |
| 19 | Rate limit | `/api/errors/429` with API key | 429 and Retry-After |
| 20 | Server failure | `/api/errors/500` | 500 |
| 21 | Timeout | `/api/delay/20` | Delayed response |
| 22 | POST | `/api/apikey/write-test` | Test record created |
| 23 | PUT | `/api/apikey/write-test/{id}` | Record replaced |
| 24 | PATCH | `/api/apikey/write-test/{id}` | Record merged |
| 25 | DELETE | `/api/apikey/write-test/{id}` | Test record deleted |
| 26 | Large source | Copy 640k `timesheet-entry` rows with 500/1000 page size | All rows in sink |
| 27 | Retry | Configure ADF retries for 429/500 | Retry behavior observed |
| 28 | Failure branch | On failure → If Condition / error logging | Correct branch executed |

## Recommended pipelines

### Pipeline A: PL_Normal_REST_Copy
- Parameters: `p_resource`, `p_auth_mode`, `p_page_size`.
- REST source: one resource endpoint.
- Copy sink: ADLS JSON or Azure SQL staging.
- First test with `labor-rate-exception` (600 rows).

### Pipeline B: PL_Paginated_REST_Copy
- Source: `timesheet-entry`.
- Page size: 1000.
- Pagination rule: `AbsoluteUrl = $.next`.
- MaxRequestNumber: `10000`.
- Compare sink count to 640,000.

### Pipeline C: PL_OAuth_Token_Then_Copy
- Web Activity calls `/oauth/token` with form-encoded body.
- Store `access_token` in a secure pipeline variable if needed (mark secure output/input).
- Copy Activity sends `Authorization: Bearer <token>`.
- For real Entra SPN, prefer ADF linked service Service Principal auth rather than manually handling the client secret.

### Pipeline D: PL_Incremental_Labor_Transaction
- Lookup last watermark from a control table.
- Copy `/api/apikey/labor-transaction?modified_since=<watermark>`.
- Get max `LastModifiedTimestamp` from staged rows.
- Update control table only after sink load succeeds.

### Pipeline E: PL_API_Error_Retry
- Call `/api/errors/429`, then `/api/errors/500`.
- Configure retry policy and failure path.
- Send error detail to a log table / notification activity.

## Count reconciliation

The source manifest lists expected source row counts. After copy, compare source counts to sink counts. Count equality is necessary but not sufficient: also compare keys, duplicates, null distributions, and column-level hashes or aggregates where appropriate.
