# ADF Mock API Platform

A reusable FastAPI-based REST API laboratory for Azure Data Factory. Includes the supplied Labor and KB CSV datasets (8 resources, 964,481 source records), five authentication modes, normal and paginated extraction, filters, incremental watermark support, error/timeout simulation, and write-test endpoints.

## Start on Windows
1. Extract the ZIP.
2. Open CMD in the extracted `ADF_Mock_API_Platform` folder.
3. Run `start_local.bat`.
4. Open `http://localhost:8000/docs`.

## Main docs
- `docs/01-architecture-and-quickstart.md`
- `docs/02-api-reference.md`
- `docs/03-authentication-and-spn.md`
- `docs/04-adf-extraction-patterns.md`
- `docs/05-add-a-new-source.md`
- `docs/06-adf-test-plan.md`

## Current resources
Labor: labor-approval, labor-rate-exception, labor-transaction, timesheet-entry.
KB: kb-article, kb-article-feedback, kb-article-usage, kb-article-view.

Add future CSV sources by updating `data/sources.json`; see `docs/05-add-a-new-source.md`.

Demo secrets are for local testing only. Replace them before exposing the service publicly. Real Entra ID SPN authentication requires your tenant and app registrations.

- `docs/07-adf-json-examples.md`
# MicrosoftSupportAPI
