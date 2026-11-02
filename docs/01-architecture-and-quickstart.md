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
