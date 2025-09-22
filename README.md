# Charter VIP / Spectrum Fabric Agent

Full-stack application consisting of:

* Frontend: Next.js 15 (App Router) served via Azure App Service
* Backend: FastAPI (Python 3.11) providing AI / Fabric Data Agent capabilities
* Infra: Provisioned with Azure Developer CLI (azd) + Bicep (`infra/main.bicep`)

## Architecture

```text
Browser -> Next.js (frontend Web App) -> /api/* rewrite -> FastAPI backend Web App
                                    -> Azure OpenAI / Language / other Azure services
```

Key Azure resources (created by Bicep):

* App Service Plan (Linux)
* Frontend Web App (Node 20 LTS)
* Backend Web App (Python 3.11)
* Application Insights (telemetry)

## Prerequisites

* Node.js 20+
* Python 3.11+
* Azure CLI: <https://learn.microsoft.com/cli/azure/install-azure-cli>
* Azure Developer CLI (azd): <https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd>
* An Azure subscription

## Environment Variables

See `.env.example` for the full list. Copy it to `.env` for local dev:

```bash
cp .env.example .env
```
Important variables:

* `BACKEND_URL` / `NEXT_PUBLIC_API_URL`: Frontend -> backend routing
* `AZURE_OPENAI_ENDPOINT`, `MODEL_DEPLOYMENT_NAME`: Azure OpenAI integration
* `LANGUAGE_ENDPOINT`, `LANGUAGE_KEY`: Azure AI Language
* Observability: `APPLICATIONINSIGHTS_CONNECTION_STRING`

In production: set via `azd env set` or App Service Configuration UI; consider Azure Key Vault for secrets.

## Local Development

Terminal 1 (backend):

```bash
cd api
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 5328 --reload
```
Terminal 2 (frontend):

```bash
npm install
npm run dev
```
Navigate to <http://localhost:3000>

## Azure Deployment (Recommended: azd)

Initialize (first time):

```bash
azd auth login
azd init --template .
```
Provision infrastructure (preview changes first):

```bash
azd provision --preview
azd provision
```
Deploy application code:

```bash
azd deploy
```
Retrieve endpoints:

```bash
azd env get-values
```
Set environment values (examples):

```bash
azd env set MODEL_DEPLOYMENT_NAME gpt-4o-mini
azd env set AZURE_OPENAI_ENDPOINT https://<your-openai>.openai.azure.com
azd env set LANGUAGE_ENDPOINT https://<your-lang>.cognitiveservices.azure.com
azd deploy
```

## Manual Deployment (Legacy Script)

A PowerShell script `deploy-to-azure.ps1` exists for manual zip deployment to two Web Apps. Prefer azd + Bicep for reproducibility.

## Infra Details

See `infra/main.bicep` for resource definitions. Key app settings applied:

* Frontend `BACKEND_URL`, `NEXT_PUBLIC_API_URL` point to backend Web App hostname
* Backend startup command: Uvicorn serving FastAPI on port 8000
* Application Insights connection string automatically injected

## Production Hardening (Next Steps)

* Add Azure Key Vault & reference secrets via `@Microsoft.KeyVault(SecretUri=...)`
* Enable Managed Identity and grant access to downstream services
* Add Health Probe endpoint (e.g. `/healthz`) in FastAPI
* Configure logging export to Log Analytics Workspace
* Add CI/CD (GitHub Actions) invoking `azd provision --preview` + `azd deploy`
* Add rate limiting / auth middleware
* Set CORS allowed origins explicitly in backend

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| 404 on /api calls | BACKEND_URL unset | Set in App Settings / redeploy |
| 500 after deploy | Missing env secret | Add via `azd env set` then `azd deploy` |
| Slow cold starts | Plan tier too small | Upgrade to P1v3 or enable Always On |
| Image optimization warnings | Using `images.unoptimized` | Configure Azure Blob / CDN and enable Next.js image opt |

## Clean Up

Delete all resources:

```bash
azd down --purge
```

## License
Internal / TBD.
