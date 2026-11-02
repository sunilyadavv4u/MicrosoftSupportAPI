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
