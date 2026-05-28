# Infinity Den

Infinity Den is a FastAPI and MongoDB content publishing platform MVP. It is being built as a modular content marketing system with public pages, reusable Jinja2 components, SEO-ready structure, newsletter and contributor workflows, and an eventual admin dashboard.

## Current Features

- FastAPI application with lifespan-managed MongoDB startup and shutdown
- Environment-driven settings via `.env`
- Async MongoDB client using Motor
- MongoDB indexes for articles, categories, tags, and newsletter subscribers
- Centralized exception handling for public pages and API responses
- JSON health check endpoint at `/health`
- Bootstrap 5 and custom static assets
- Jinja2 base layout with reusable navbar and footer partials
- Responsive homepage with hero content, featured articles, latest articles, category showcase, newsletter signup, and article cards
- Graceful local development mode when MongoDB is unavailable

## Tech Stack

- Python 3.12+
- FastAPI
- MongoDB
- Motor
- Jinja2
- Bootstrap 5
- JavaScript and jQuery

## Project Structure

```text
app/
├── config/          # Settings and constants
├── database/        # MongoDB connection and indexes
├── routes/          # Public, admin, and API routes
├── services/        # Business logic and data access
├── templates/       # Layouts, pages, partials, and components
└── static/          # CSS, JavaScript, images, and fonts
```

## Getting Started

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a local `.env` file from the example template:

```bash
cp .env.example .env
```

Then adjust the values for your local environment:

```env
APP_NAME=Infinity Den
APP_ENV=development
DEBUG=true
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO
LOG_FORMAT=plain
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=infinity_den
MONGODB_REQUIRED=false
MONGODB_SERVER_SELECTION_TIMEOUT_MS=2000
```

Run the application:

```bash
python run.py
```

The homepage will be available at [http://127.0.0.1:8000](http://127.0.0.1:8000).

Check application health:

```bash
curl http://127.0.0.1:8000/health
```

## Configuration

The app reads configuration from `.env` through `app/config/settings.py`.

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `Infinity Den` | Application display name |
| `APP_ENV` | `development` | Runtime environment label |
| `DEBUG` | `false` | Enables Uvicorn reload when running `run.py` |
| `HOST` | `127.0.0.1` | Development server host |
| `PORT` | `8000` | Development server port |
| `LOG_LEVEL` | `INFO` | Console log level such as `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `LOG_FORMAT` | `plain` | Console log format; use `plain` or `detailed` |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection URI |
| `MONGODB_DB_NAME` | `infinity_den` | MongoDB database name |
| `MONGODB_REQUIRED` | `false` | Fail startup if MongoDB is unavailable |
| `MONGODB_SERVER_SELECTION_TIMEOUT_MS` | `2000` | MongoDB connection timeout |

## Development Notes

- Keep routes focused on request and response handling.
- Put business rules and database interaction in services.
- Use reusable templates for repeated UI.
- Add Pydantic schemas for validation as API features are introduced.
- Keep secrets in `.env`, keep `.env.example` safe to commit, and document new environment variables in both places.

## Verification

Basic import check:

```bash
python -m compileall app
```

Run the local server:

```bash
python run.py
```
