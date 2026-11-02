# ADF Mock API Platform — Complete Implementation Guide

This guide combines architecture, setup, API reference, authentication/SPN, ADF extraction patterns, extensibility, deployment and test plan. The full individual guides are also in the `docs/` folder.



---

# ADF Mock API Platform — Architecture and Quick Start

## Purpose

A reusable, dataset-backed REST API laboratory for Azure Data Factory. The current package includes the Labor and Knowledge Base (`kb`) CSV domains supplied with this project. The framework is designed so another CSV source can be added through the manifest without writing new endpoint code.

## Current source inventory

| Resource URL | SQLite table | CSV rows |
|---|---|---:|
| `labor-approval` | `SrcLaborApproval` | 24,642 |
| `labor-rate-exception` | `SrcLaborRateException` | 600 |
| `labor-transaction` | `SrcLaborTransaction` | 30,129 |
| `timesheet-entry` | `SrcTimesheetEntry` | 640,000 |
| `kb-article` | `SrcKBArticle` | 14,000 |
| `kb-article-feedback` | `SrcKBArticleFeedback` | 60,000 |
| `kb-article-usage` | `SrcKBArticleUsage` | 15,110 |
| `kb-article-view` | `SrcKBArticleView` | 180,000 |
| **Total** | **8 resources** | **964,481** |

## Architecture

```text
CSV files (Labor + KB + future source folders)
                 |
                 v
        scripts/load_data.py
                 |
                 v
      Local SQLite read store
                 |
                 v
        FastAPI REST service
      /        |         |       \
 API Key     Basic     Bearer    OAuth2 / Entra
                 |
                 v
        ADF REST Linked Service
                 |
                 v
      Copy / Web / Lookup / ForEach
                 |
                 v
       Azure SQL / ADLS / Fabric
```

The SQLite database is a local mock-data store. It allows repeatable paging and filtering without loading large CSV files into memory on every API request. All source CSVs are retained in `data/`.

## Windows quick start

Requirements: Python 3.11+.

1. Extract the ZIP to a short local path, for example `C:\\D\\ADF_Mock_API_Platform`.
2. Open CMD in that folder.
3. Run:

```cmd
start_local.bat
```

The script creates `.venv`, installs requirements, copies `.env.example` to `.env`, loads source CSVs once if the SQLite database does not exist, then starts Uvicorn.

If you change or replace CSVs and want to reload them:

```cmd
.venv\\Scripts\\activate
python scripts\\load_data.py --reload
```

Open:
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI: `http://localhost:8000/openapi.json`
- Health: `http://localhost:8000/health`
- Source metadata: `http://localhost:8000/api/metadata`

## Local sample credentials

The `.env.example` file contains intentionally weak demo credentials. They are for local isolated testing only.

| Authentication | Demo setting |
|---|---|
| API Key | Header `x-api-key: change-me-local-api-key` |
| Basic | `adf_user` / `ChangeThis_Basic_123!` |
| Static Bearer | `Authorization: Bearer change-me-static-bearer-token` |
| Local OAuth client | `adf-spn-client` / `ChangeThis_OAuth_Secret_123!` |
| Entra ID SPN | Your own tenant, API app registration, client app registration, role and secret/certificate |

Before using a tunnel or public cloud host, replace all demo secrets with long random values. Never commit `.env` to source control.


---

# API Reference

All data endpoints are GET and read from the eight CSV-derived tables. The same resource URL is available under each authentication prefix.

## Resource endpoints

| Auth prefix | Example |
|---|---|
| API Key | `/api/apikey/labor-transaction` |
| Basic | `/api/basic/labor-transaction` |
| Static Bearer | `/api/bearer/labor-transaction` |
| Local OAuth2 | `/api/oauth/labor-transaction` |
| Microsoft Entra ID | `/api/entra/labor-transaction` |

Resources:
- `labor-approval`
- `labor-rate-exception`
- `labor-transaction`
- `timesheet-entry`
- `kb-article`
- `kb-article-feedback`
- `kb-article-usage`
- `kb-article-view`

## Query parameters

| Parameter | Meaning | Example |
|---|---|---|
| `page` | 1-based page number | `page=3` |
| `page_size` | Rows per page (max 1000) | `page_size=500` |
| `pagination` | `page`, `offset`, or `none` | `pagination=offset` |
| `offset` | Zero-based starting row | `offset=1000` |
| `limit` | Page size for offset mode | `limit=1000` |
| `response_format` | `envelope`, `odata`, or `array` | `response_format=odata` |
| `vendor_code` | Filter resources containing VendorCode | `vendor_code=VEN-IMPT` |
| `employee_email` | Filter resources containing EmployeeEmail | `employee_email=a@x.com` |
| `ticket_number` | Filter resources containing TicketNumber | `ticket_number=2405070000000001` |
| `approval_status` | ApprovalStatus equality filter | `approval_status=Approved` |
| `submission_status` | SubmissionStatus equality filter | `submission_status=Approved` |
| `activity_type` | ActivityType equality filter | `activity_type=Repro` |
| `status` | Status equality filter | `status=Published` |
| `product_code` | ProductCode equality filter | `product_code=M365-TEAMS` |
| `article_code` | ArticleCode equality filter | `article_code=KB0000001` |
| `date_from` / `date_to` | Range on the resource's detected date field | `date_from=2024-01-01` |
| `modified_since` | Incremental filter; requires LastModifiedTimestamp | `modified_since=2024-05-07%2000:00:00` |
| `order_by` | Sort by a valid column name | `order_by=WorkDate` |

Filters that do not apply to a resource are ignored. Date ranges use the first matching date column in this order: WorkDate, WeekStartDate, PublishedDate, FeedbackDate, ViewedTimestamp, ViewTimestamp, ApprovalTimestamp, LastModifiedTimestamp, EffectiveFrom. `modified_since` is supported only for a resource that has `LastModifiedTimestamp` (currently `labor-transaction`).

## Response formats

### Envelope (default)
```json
{
  "resource": "labor-transaction",
  "authentication": "api-key",
  "page": 1,
  "offset": 0,
  "page_size": 100,
  "total_records": 30129,
  "returned_records": 100,
  "has_more": true,
  "next_page": 2,
  "next_offset": null,
  "next": "http://localhost:8000/api/apikey/labor-transaction?page=2&page_size=100",
  "data": []
}
```

### OData-style
`?response_format=odata`

```json
{
  "@odata.count": 30129,
  "value": [],
  "@odata.nextLink": "http://localhost:8000/api/apikey/labor-transaction?page=2&page_size=100&response_format=odata"
}
```

### Plain JSON array
`?response_format=array`

Returns a top-level JSON array. Useful for a simple HTTP client, but ADF REST connector pagination is not supported for top-level array responses. Use `envelope` or `odata` when using ADF pagination.

## Non-data endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Service welcome |
| GET | `/health` | Health and loaded row counts |
| GET | `/api/metadata` | Resource/table/column inventory |
| POST | `/oauth/token` | Local OAuth2 client-credentials token |
| GET | `/api/errors/{status_code}` | Simulate HTTP errors; API key required |
| GET | `/api/delay/{seconds}` | Simulate latency; API key required |
| POST | `/api/apikey/write-test` | Insert disposable test record |
| GET | `/api/apikey/write-test/{id}` | Read disposable test record |
| PUT | `/api/apikey/write-test/{id}` | Replace disposable test record |
| PATCH | `/api/apikey/write-test/{id}` | Partially update disposable test record |
| DELETE | `/api/apikey/write-test/{id}` | Delete disposable test record |

Write-test routes are intentionally separate from source tables. They do not mutate the CSV-derived source data.


---

# Authentication Guide — API Key, Basic, Bearer, OAuth2 and Entra SPN

## Authentication matrix

| Mode | How client authenticates | ADF configuration |
|---|---|---|
| Anonymous | No credential | REST linked service: Anonymous |
| API Key | `x-api-key` header | Anonymous + `authHeaders` / additional header |
| Basic | Username and password | REST linked service: Basic |
| Static Bearer | Fixed demo token | Anonymous + `Authorization: Bearer ...` header |
| Local OAuth2 | Client ID/secret to this mock token endpoint | Web Activity gets token, then pass Bearer header; or configure OAuth2 Client Credential where endpoint/client auth style matches |
| Microsoft Entra SPN | Real Entra-issued JWT for this API audience | REST linked service: Service Principal (`AadServicePrincipal`) or OAuth2 Client Credential, depending on linked-service UI |

ADF's REST connector documents Anonymous, Basic, Service Principal, OAuth2 Client Credential, System Assigned Managed Identity, and User Assigned Managed Identity. API key can be supplied as an auth header with Anonymous. See Microsoft Learn: https://learn.microsoft.com/azure/data-factory/connector-rest

## 1. API Key

Request:
```http
GET /api/apikey/labor-transaction?page=1&page_size=100
x-api-key: <API_KEY>
```

ADF:
- Linked service authentication: Anonymous
- Additional authentication header: `x-api-key`
- Value: Key Vault secret reference preferred
- Relative URL: `/api/apikey/labor-transaction?page=1&page_size=100`

## 2. Basic authentication

Request:
```http
GET /api/basic/timesheet-entry?page=1&page_size=100
Authorization: Basic <base64(username:password)>
```

ADF:
- Authentication: Basic
- Username/password from Key Vault or secure parameters
- Relative URL: `/api/basic/timesheet-entry`

## 3. Static Bearer

Request:
```http
GET /api/bearer/kb-article?page=1&page_size=100
Authorization: Bearer <STATIC_BEARER_TOKEN>
```

ADF:
- Authentication: Anonymous
- Additional header: `Authorization`
- Value: `Bearer <token>`
- Store token in Key Vault; do not hardcode it in pipeline JSON.

## 4. Local OAuth2 client-credentials simulator

Token endpoint:
`POST https://<host>/oauth/token`

Content-Type:
`application/x-www-form-urlencoded`

Form body:
```text
grant_type=client_credentials
client_id=<OAUTH_CLIENT_ID>
client_secret=<OAUTH_CLIENT_SECRET>
```

Example cURL:
```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=adf-spn-client&client_secret=ChangeThis_OAuth_Secret_123!"
```

Response:
```json
{
  "access_token": "<signed JWT>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "Data.Read Data.Write"
}
```

Then call:
```http
GET /api/oauth/labor-transaction?page=1&page_size=100
Authorization: Bearer <access_token>
```

ADF implementation:
1. Web Activity `Get_Local_OAuth_Token` calls `/oauth/token` using POST and form-encoded body.
2. Parse `access_token` from the Web Activity output.
3. Copy Activity REST source adds header:
   `Authorization = @concat('Bearer ', activity('Get_Local_OAuth_Token').output.access_token)`
4. Use `/api/oauth/<resource>` as relative URL.

This local token issuer is a learning simulator. It demonstrates client-credentials token acquisition and JWT validation, but it is not an externally trusted authorization server and is not production-grade OAuth infrastructure.

## 5. Microsoft Entra ID — real SPN / client credentials

This is the recommended way to practise real Service Principal authentication. The API validates Microsoft-signed JWTs using the tenant's published JWKS, and checks signature, issuer, audience, and a delegated scope or application role.

### A. Register the API application

1. Microsoft Entra admin center → App registrations → New registration.
2. Name: `adf-mock-api`.
3. Record the API app's Application (client) ID and Directory (tenant) ID.
4. Under Expose an API, set Application ID URI, for example:
   `api://<API-APP-CLIENT-ID>`
5. Add an application role:
   - Display name: `Labor and KB Read`
   - Value: `Data.Read.All`
   - Allowed member types: Applications
   - Enable the role.
6. Optional: expose delegated scope `Data.Read` for delegated-user testing.

### B. Register the ADF client / SPN

1. Create another app registration, e.g. `adf-mock-api-client`.
2. Create a client secret (or use a certificate in production).
3. Under API permissions, add permission → My APIs → `adf-mock-api`.
4. Select application permission `Data.Read.All`.
5. Grant admin consent.
6. Assign the API app role to the enterprise application/service principal if required by your tenant's consent/assignment settings.
7. Store the client secret in Azure Key Vault.

### C. Configure API environment

In the API host's environment settings (or local `.env` for local development):
```dotenv
ENTRA_TENANT_ID=<TENANT-GUID>
ENTRA_AUDIENCE=api://<API-APP-CLIENT-ID>
ENTRA_ISSUER=https://login.microsoftonline.com/<TENANT-GUID>/v2.0
ENTRA_REQUIRED_SCOPE=Data.Read
ENTRA_REQUIRED_ROLE=Data.Read.All
```
Restart the API after changing these settings.

The API's `/api/entra/...` routes validate real Entra JWTs. For application-only tokens, the `roles` claim must include `Data.Read.All`. For delegated tokens, the `scp` claim must include `Data.Read`.

### D. Acquire an Entra token with SPN

Token endpoint:
`https://login.microsoftonline.com/<TENANT-GUID>/oauth2/v2.0/token`

Form body:
```text
client_id=<ADF-CLIENT-APP-ID>
client_secret=<ADF-CLIENT-SECRET>
grant_type=client_credentials
scope=api://<API-APP-CLIENT-ID>/.default
```

The token's `aud` must match `ENTRA_AUDIENCE` exactly. The token must contain the API role `Data.Read.All`.

PowerShell example:
```powershell
$tenantId = "<TENANT-GUID>"
$clientId = "<ADF-CLIENT-APP-ID>"
$clientSecret = "<CLIENT-SECRET>"
$scope = "api://<API-APP-CLIENT-ID>/.default"

$body = @{
  client_id = $clientId
  client_secret = $clientSecret
  grant_type = "client_credentials"
  scope = $scope
}

$token = Invoke-RestMethod `
  -Method Post `
  -Uri "https://login.microsoftonline.com/$tenantId/oauth2/v2.0/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body $body

$headers = @{ Authorization = "Bearer $($token.access_token)" }
Invoke-RestMethod -Uri "https://<API-HOST>/api/entra/labor-transaction?page=1&page_size=10" -Headers $headers
```

### E. ADF Service Principal linked service

For the REST linked service, select Service Principal authentication where available:
- Service principal ID: ADF client app ID
- Service principal key: Key Vault secret
- Tenant: tenant ID
- Audience / resource: API Application ID URI (`api://<API-APP-CLIENT-ID>`) as required by the ADF REST linked service UI.

The REST connector's Service Principal auth acquires a token for the configured resource. Verify the token's `aud` matches the API's `ENTRA_AUDIENCE`. Depending on the connector UI/version, use OAuth2 Client Credential if that is the supported mode for your API endpoint. Do not send a token intended for Microsoft Graph to this API; the audience must be your API.

### F. SPN versus Bearer

- SPN is the client identity used to request a token from Microsoft Entra ID.
- Bearer is how the access token is presented to the API:
  `Authorization: Bearer <access_token>`.
- ADF Service Principal authentication obtains and sends the bearer token for you.
- If using Web Activity to acquire the token manually, you must add the Authorization header yourself.

Never paste real secrets or access tokens into source code, Git, or screenshots. Use Key Vault and rotate credentials if exposed.


---

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


---

# Add another source / dataset without changing API code

The API is manifest-driven. To add a new source, add CSV files and one table entry in `data/sources.json`. The same API route, authentication methods, pagination, filtering and response formats will become available automatically.

## Steps

1. Create a folder under `data/`, for example `data/finance/`.
2. Copy your CSV into that folder, e.g. `SrcInvoice.csv`.
3. Add an entry in `data/sources.json`:
```json
{
  "resource": "invoice",
  "table": "SrcInvoice",
  "domain": "finance",
  "file": "data/finance/SrcInvoice.csv",
  "rows": 12500,
  "columns": ["InvoiceID", "CustomerID", "InvoiceDate", "Amount"]
}
```
4. Keep `resource` URL-friendly, lowercase, and unique.
5. Ensure `table` is a safe SQL identifier (letters, digits, underscore; do not use untrusted identifiers).
6. Run:
```cmd
python scripts\\load_data.py --reload
```
7. Restart the API and check `/api/metadata` and `/health`.
8. New endpoints are now available:
   - `/api/apikey/invoice`
   - `/api/basic/invoice`
   - `/api/bearer/invoice`
   - `/api/oauth/invoice`
   - `/api/entra/invoice`

## CSV rules

- First row must be a header.
- UTF-8 or UTF-8 with BOM is supported.
- Quoted commas, escaped quotes and multiline quoted fields are handled by Python's CSV reader.
- Every row should have the same logical columns as the header.
- Values are retained as text in SQLite and returned as JSON strings. Cast them in ADF mapping or downstream SQL as required.
- `rows` in the manifest is documentation/expected count; actual counts are calculated at load time.

## Multiple files for one logical source

Combine the files into one CSV before loading, or extend `scripts/load_data.py` to read a list of files for the same table. Do not create multiple manifest entries with the same table name.

## Optional source-specific filters

The common query filters are implemented centrally in `app/main.py`. To add a custom query filter:
1. Add a typed query parameter to `make_resource_handler.handler`.
2. Add it to the `filters` dictionary using the exact CSV column name.
3. The store only applies filters for columns that exist in the chosen table.
4. Document the filter in `docs/02-api-reference.md`.

## Incremental extraction

The generic API supports `modified_since` only if a source has a `LastModifiedTimestamp` column. If a new source uses another watermark column, extend `query_resource` to accept a `watermark_column` / `watermark_value` pair. For reliable production incremental extraction, keep the watermark in ADF control tables and advance it only after sink success.


---

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


---

# ADF JSON examples (illustrative templates)

These are starting templates for the ADF UI / Git mode. Replace names, URLs, Key Vault references, integration runtime names, and sink datasets with your environment. ADF exports can vary by API version.

## REST linked service — API Key (Anonymous + auth header)

```json
{
  "name": "LS_REST_MockAPI_ApiKey",
  "properties": {
    "type": "RestService",
    "typeProperties": {
      "url": "https://<API-HOST>",
      "enableServerCertificateValidation": true,
      "authenticationType": "Anonymous",
      "authHeaders": {
        "x-api-key": {
          "type": "SecureString",
          "value": "<STORE-OR-REFERENCE-KEY-VAULT-SECRET>"
        }
      }
    }
  }
}
```

For local SHIR, set URL to `http://<SHIR-HOST>:8000` (or `http://localhost:8000` only if SHIR runs on the same machine).

## REST dataset

```json
{
  "name": "DS_REST_LaborTransaction",
  "properties": {
    "linkedServiceName": {
      "referenceName": "LS_REST_MockAPI_ApiKey",
      "type": "LinkedServiceReference"
    },
    "type": "RestResource",
    "typeProperties": {
      "relativeUrl": "/api/apikey/labor-transaction?page=1&page_size=1000"
    }
  }
}
```

## Copy Activity source pagination

Configure this under Copy Activity → Source → Pagination rules:

```json
{
  "AbsoluteUrl": "$.next",
  "MaxRequestNumber": "10000"
}
```

For OData response use relative URL ending in `&response_format=odata` and rule:
```json
{
  "AbsoluteUrl": "$['@odata.nextLink']",
  "MaxRequestNumber": "10000"
}
```

## Basic authentication linked service (conceptual)

Use `authenticationType: "Basic"` and supply username/password using SecureString or Key Vault. Create a distinct linked service with base URL and point the dataset relative URL to `/api/basic/<resource>`.

## Service Principal linked service (real Entra ID)

The REST linked service supports Service Principal authentication. Configure:
- `authenticationType`: `AadServicePrincipal`
- `servicePrincipalId`: ADF client application ID
- `servicePrincipalKey`: Key Vault secret reference
- `tenant`: tenant GUID
- `aadResourceId` / audience: API Application ID URI, e.g. `api://<API-APP-CLIENT-ID>` (field name depends on ADF linked service model/version).

Use relative URL `/api/entra/labor-transaction`. The resulting access token's audience must match the API's `ENTRA_AUDIENCE` and contain app role `Data.Read.All`.

## Web Activity: get local OAuth2 token

Web Activity URL:
`https://<API-HOST>/oauth/token`

Method: POST

Headers:
```json
{
  "Content-Type": "application/x-www-form-urlencoded"
}
```

Body:
```text
grant_type=client_credentials&client_id=<CLIENT_ID>&client_secret=<CLIENT_SECRET>
```

Mark secure input/output on activities that handle credentials or tokens. Store the client secret in Key Vault. The local mock OAuth issuer accepts client credentials in form fields. For real SPN authentication, use Entra's token endpoint and prefer ADF Service Principal linked-service auth.

After Web Activity, a Copy Activity additional header can use a dynamic expression equivalent to:
```text
@concat('Bearer ', activity('Get_Local_OAuth_Token').output.access_token)
```

The REST source should call `/api/oauth/labor-transaction`.

## ForEach page-number pattern (alternative to connector pagination)

Use when learning manual orchestration:
1. Lookup `/api/metadata` or obtain total_records from first response.
2. Calculate page count: `ceil(total_records / page_size)`.
3. Generate page numbers in a ForEach.
4. Call each page URL and write to a sink.
5. Set batch count/concurrency conservatively to avoid overwhelming the source.

Connector-driven `AbsoluteUrl = $.next` pagination is usually simpler and avoids manually calculating the page count.
