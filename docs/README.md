# ADF Mock API Platform

A reusable FastAPI-based REST API laboratory for Azure Data Factory. Includes the supplied Labor and KB CSV datasets (8 resources, 964,481 source records), five authentication modes, normal and paginated extraction, filters, incremental watermark support, error/timeout simulation, and write-test endpoints.

## Start on Windows (explicit setup)

**Prerequisite:** Install Python 3.11 or later (64-bit). Python 3.14 is also supported by this project when its dependencies install successfully. During installation, enable **Add Python to PATH**.

1. Extract the ZIP.
2. Open Command Prompt (CMD) in the extracted `ADF_Mock_API_Platform` folder.
3. Verify Python is available:

   ```cmd
   python --version
   py --version
   ```

4. Create a project-specific virtual environment (run this once):

   ```cmd
   python -m venv .venv
   ```

   You can use `py -m venv .venv` instead. Both commands create the `.venv` folder in the project directory.

5. Activate the virtual environment:

   ```cmd
   .venv\Scripts\activate
   ```

   Your command prompt should now show `(.venv)` at the beginning.

6. Upgrade pip and install project dependencies:

   ```cmd
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

7. Create your local environment file:

   ```cmd
   copy .env.example .env
   ```

   If `.env` already exists, keep your existing configuration rather than overwriting it.

8. Load the sample CSV data into the local SQLite database (first setup only):

   ```cmd
   python scripts\load_data.py
   ```

9. Start the API:

   ```cmd
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

10. Open `http://localhost:8000/docs`.

**Alternative:** After completing the setup once, you can run `start_local.bat` to activate the environment, install/check dependencies, load data if needed, and start the API.

To exit the virtual environment, run `deactivate`. To use the project again, open CMD in the project folder and run `.venv\Scripts\activate` before running Python commands.

## Main docs
- `docs/01-architecture-and-quickstart.md`
- `docs/02-api-reference.md`
- `docs/03-authentication-and-spn.md`
- `docs/04-adf-extraction-patterns.md`
- `docs/05-add-a-new-source.md`
- `docs/06-adf-test-plan.md`
- `docs/07-adf-json-examples.md`

## Current resources
Labor: labor-approval, labor-rate-exception, labor-transaction, timesheet-entry.
KB: kb-article, kb-article-feedback, kb-article-usage, kb-article-view.

Add future CSV sources by updating `data/sources.json`; see `docs/05-add-a-new-source.md`.

Demo secrets are for local testing only. Replace them before exposing the service publicly. Real Entra ID SPN authentication requires your tenant and app registrations.
