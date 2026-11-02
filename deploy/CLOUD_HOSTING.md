# Cloud hosting: Azure Container Apps / App Service for Containers

The Dockerfile builds the API and seeds its SQLite read database from the CSV files. Use a container-based host to provide a public HTTPS URL for Azure Data Factory's Azure Integration Runtime.

## Azure Container Apps outline

1. Create an Azure Container Registry or use another supported container registry.
2. Build and push the image from the project root:
   ```bash
   docker build -f deploy/Dockerfile -t <registry>.azurecr.io/adf-mock-api:1.0 .
   docker push <registry>.azurecr.io/adf-mock-api:1.0
   ```
3. Create an Azure Container App using the image.
4. Enable ingress (external for public testing) on target port 8000.
5. Configure environment variables in the Container App. Never bake `.env` or credentials into the image.
6. Replace all demo secrets. Set `ENTRA_TENANT_ID`, `ENTRA_AUDIENCE`, `ENTRA_ISSUER` and required scope/role.
7. Verify `https://<container-app-fqdn>/health` and `/docs`.

## Important data persistence note

The source data is baked into the image and loaded into SQLite when building the image. This is suitable for read-only API extraction tests. API write-test records are stored in SQLite and may be lost if the container is replaced/restarted or a new replica receives the request. Do not use local SQLite for shared multi-replica production state. For persistent writes, move the write-test store to Azure SQL or another managed database.

## Free / low-cost note

Cloud hosting may have a free grant or consumption pricing depending on region, subscription, and current offer. Registry, logs, storage, outbound data and idle resources can still cost money. Set budgets/alerts and delete resources after practice. Local hosting with Self-hosted IR is the no-cloud-hosting-cost option.
