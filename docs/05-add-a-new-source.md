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
