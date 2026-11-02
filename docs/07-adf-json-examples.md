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
