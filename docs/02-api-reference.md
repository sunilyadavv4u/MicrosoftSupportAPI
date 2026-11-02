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
