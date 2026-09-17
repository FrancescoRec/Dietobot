<div align="center">
  <img src="logo.gif" alt="DietoBot apple logo" width="420">
  <h1>DietoBot</h1>
  <p><strong>A conversational nutrition assistant that turns a friendly chat into a useful personal profile and daily nutrition targets.</strong></p>
</div>

## What is DietoBot?

DietoBot is a Django web app that collects a user's nutrition details through conversation. It uses Gemini on Google Vertex AI to understand each answer, stores the resulting profile, and calculates personalized calorie and macronutrient targets. Users can create an account, open one chat, and continue the same conversation later.

## What it includes

- Account signup, login, and logout
- A persistent chat history for each user
- Guided collection of age, sex, height, weight, activity level, and goal
- Optional preferences such as allergies, disliked foods, cooking time, and budget
- Calorie and macronutrient calculations
- Gemini models through Google Vertex AI; no Gemini API key is required
- PostgreSQL and Docker support, plus SQLite for lightweight local development
- Responsive pages designed for desktop and phone screens

## Quick start with Docker

### 1. Requirements

Install these tools before starting:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Google Cloud CLI](https://cloud.google.com/sdk/docs/install)
- Access to a Google Cloud project with billing enabled

The commands below use `dietobot` as the Google Cloud project ID. Replace it if your project has a different ID.

### 2. Create the environment file

From the project directory, run:

```powershell
Copy-Item env.example .env
```

Open `.env` and set a unique `SECRET_KEY`. The included database values already match `docker-compose.yml`.

### 3. Configure Vertex AI

Sign in, select the project, enable Vertex AI, and create Application Default Credentials:

```powershell
gcloud auth login
gcloud config set project dietobot
gcloud services enable aiplatform.googleapis.com --project=dietobot
gcloud auth application-default login
gcloud auth application-default set-quota-project dietobot
```

On Windows, Google Cloud CLI creates the credentials file under `%APPDATA%\gcloud`. Docker Compose mounts that file into the Django container at `/gcp/adc.json`.

Your Google account needs permission to use Vertex AI. The app currently uses `gemini-2.5-flash` for structured extraction and `gemini-2.5-flash-lite` for conversational replies.

### 4. Start the app

```powershell
docker compose up --build
```

Docker starts PostgreSQL, applies the Django migrations, and serves the app. Open [http://localhost:8000](http://localhost:8000), create an account, and select **Go to chat**.

Stop the app with `Ctrl+C`. Start it again later with:

```powershell
docker compose up
```

## Local setup without Docker

This option uses SQLite, so PostgreSQL is not required. Python 3.11 or newer and Google Cloud CLI are still required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item env.example .env
```

In `.env`, change:

```env
USE_SQLITE=true
```

Then authenticate with Google Cloud and start Django:

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project dietobot
python manage.py migrate
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Environment settings

| Variable | Purpose | Development example |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | Selects Django settings | `config.settings.local` |
| `SECRET_KEY` | Signs Django sessions and security data | Use a private random value |
| `DEBUG` | Enables local debug pages | `True` |
| `DB_NAME` | PostgreSQL database name | `dietobot` |
| `DB_USER` | PostgreSQL user | `postgres` |
| `DB_PASSWORD` | PostgreSQL password | `postgres` |
| `DB_HOST` | PostgreSQL host | `db` in Docker |
| `DB_PORT` | PostgreSQL port inside Docker | `5432` |
| `USE_SQLITE` | Uses SQLite instead of PostgreSQL | `false` |
| `GOOGLE_CLOUD_PROJECT` | Vertex AI project ID | `dietobot` |
| `ALLOWED_HOSTS` | Production host names | Your deployed domain |

Do not commit `.env` or Google credentials.

## Useful commands

Run commands in Docker:

```powershell
docker compose run --rm django python manage.py migrate
docker compose run --rm django python manage.py createsuperuser
docker compose run --rm django python manage.py test
docker compose logs -f django
```

Run the tests locally with SQLite:

```powershell
$env:USE_SQLITE = "true"
python manage.py test
```

## Project map

```text
ai/                    Gemini extraction and LangGraph conversation workflow
chat/                  Chat view, messages, URLs, templates, and tests
core/                  Home page, authentication templates, and shared design
nutrition/             Calorie and macronutrient calculations
profiles/              Stored nutrition profile and validation
config/settings/       Shared, local, and production Django settings
logo.gif               Logo shown here in the README
core/static/images/logo.gif Logo served by the web app
```

The main routes are:

- `/` - home after login
- `/dietobot/` - nutrition chat
- `/accounts/signup/` - create an account
- `/accounts/login/` - log in
- `/accounts/logout/` - log out with a POST request
- `/admin/` - Django administration

## Troubleshooting

**Vertex AI says credentials are missing**

Run `gcloud auth application-default login` again. With Docker Desktop on Windows, confirm that `%APPDATA%\gcloud\application_default_credentials.json` exists before starting Compose.

**Vertex AI returns a permission or quota error**

Confirm billing is enabled, the Vertex AI API is enabled, the signed-in account can use Vertex AI, and the ADC quota project matches `GOOGLE_CLOUD_PROJECT`.

**PostgreSQL cannot connect**

Make sure `.env` uses `DB_NAME=dietobot`, `DB_HOST=db`, and `DB_PORT=5432`. Port `5433` is only the host-machine mapping used by database tools outside Docker.

**A database table is missing**

Apply migrations with `docker compose run --rm django python manage.py migrate` or `python manage.py migrate` for local SQLite.

**Static files are missing in production**

Run `python manage.py collectstatic --noinput`. The production startup script already performs this step before Gunicorn starts.

## Production

The repository includes `Dockerfile`, `start.sh`, Gunicorn, WhiteNoise, and `config.settings.prod`. A production deployment must provide `DJANGO_SETTINGS_MODULE=config.settings.prod`, a strong `SECRET_KEY`, `ALLOWED_HOSTS`, a PostgreSQL `DATABASE_URL`, and Google Cloud credentials that Vertex AI can use. HTTPS is required by the production settings.
