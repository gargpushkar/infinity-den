# Infinity Den

Infinity Den is a community knowledge platform built with FastAPI and MongoDB: a place where people discover ideas, contribute lived experience, discuss questions, and learn through short games.

- `vision.md` — what the product is and what each phase includes
- `instructions.md` — architecture, conventions, and development rules
- `tasks.md` — progress tracker
- `admin.md` — admin roadmap

## Current Features

- FastAPI application with lifespan-managed MongoDB startup and shutdown
- Environment-driven settings via `.env`
- Async MongoDB client using Motor
- MongoDB indexes for articles, categories, tags, and newsletter subscribers
- Centralized exception handling for public pages and API responses
- JSON health check endpoint at `/health`
- Bootstrap 5 and custom static assets
- Jinja2 base layout with reusable navbar and footer partials
- Homepage in the vision order: hero, Today's Question, the Human Library, a Fact or Fiction card answered in place, rooms, editor picks, community pieces, and an invitation to write
- Day and night modes: follows the device until the visitor picks one with the header switch
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
MONGODB_DB_NAME=infinity_den_dev
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

Seed the six launch rooms and sample pieces into a development database
(`MONGODB_DB_NAME` must end in `_dev`; the script refuses anything else):

```bash
python -m scripts.seed_dev_data            # preview
python -m scripts.seed_dev_data --apply    # write
```

The sample pieces are placeholders credited to "Sample writer". Rerunning is safe.

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
| `AUTH_SECRET_KEY` | *(empty)* | Signs sign-in tokens and form tokens; required, and different in every environment |
| `AUTH_TOKEN_EXPIRE_MINUTES` | `60` | How long an admin session lasts |
| `MEMBER_TOKEN_EXPIRE_DAYS` | `30` | How long a member session lasts |
| `AUTH_COOKIE_SECURE` | `false` | Send cookies over HTTPS only; `true` in production |
| `SITE_TIMEZONE` | `America/New_York` | When "today's question" changes |
| `MEDIA_DIR` | `media` | Where uploaded cover images are stored (served at `/media/`) |
| `CONTACT_EMAIL` | the owner's address | Shown in the footer and on the policy pages for questions and data requests |
| `SITE_URL` | *(empty)* | Public address for links in emails, e.g. `https://infinityden.com`; required in production |
| `SMTP_HOST` | *(empty)* | Outgoing mail server; empty means emails are logged instead of sent |
| `SMTP_PORT` | `587` | `587` or `2525` (STARTTLS), or `465` (TLS) |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | *(empty)* | The SMTP login and key from the email provider |
| `MAIL_FROM` | `Infinity Den <noreply@infinityden.com>` | Sender of every email; replies go to `CONTACT_EMAIL` |

`APP_ENV=production` also turns off the API docs (`/docs`, `/redoc`, `/openapi.json`).

## Production setup (fresh database)

1. **Atlas.** Put the cluster in the same region as the app server (every page
   makes several database round trips). Use a new database name such as
   `infinity_den_prod`; not `infinity_den`, which holds the previous site's
   data. Create a database user with `readWrite` on that database only, allow
   only the server's IP, and turn on backups.
2. **`.env` on the server:**

   ```env
   APP_ENV=production
   DEBUG=false
   HOST=127.0.0.1
   PORT=8000
   MONGODB_URI=<the production user's connection string>
   MONGODB_DB_NAME=infinity_den_prod
   MONGODB_REQUIRED=true
   MONGODB_SERVER_SELECTION_TIMEOUT_MS=5000
   AUTH_SECRET_KEY=<python -c "import secrets; print(secrets.token_urlsafe(48))">
   AUTH_COOKIE_SECURE=true
   SITE_TIMEZONE=America/New_York
   MEDIA_DIR=/var/lib/infinity-den/media
   SITE_URL=https://infinityden.com
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USERNAME=<Brevo SMTP login>
   SMTP_PASSWORD=<Brevo SMTP key>
   MAIL_FROM=Infinity Den <noreply@infinityden.com>
   ```

   Always set `MONGODB_DB_NAME`: the code default is `infinity_den`.
   `MEDIA_DIR` holds uploaded covers: put it outside the code checkout so
   deploys keep it, make it writable by the app user, and back it up (Atlas
   backups don't include it).
3. **Run** one uvicorn worker behind nginx with `--proxy-headers
   --forwarded-allow-ips=127.0.0.1`, so links are `https://`. (Rate limits live
   in memory, so several workers would each keep their own counts.) Cover
   uploads are up to 5 MB and nginx refuses bodies over 1 MB by default, so
   add `client_max_body_size 6m;` to the site's `server` block.
4. **First run.** Start the app once; it creates every index. Then, on the
   server with the production `.env`:

   ```bash
   python scripts/create_admin.py                 # your admin account
   python scripts/create_launch_rooms.py          # preview the six rooms
   python scripts/create_launch_rooms.py --apply  # create them
   ```

   The rooms script only adds rooms that are missing and never changes ones
   editors have edited. Never run `seed_dev_data.py` here; it refuses any
   database whose name does not end in `_dev`.
5. **Launch content, in admin.** Homepage sections hide when they are empty,
   so before launch add: a week of questions, a handful of Fact or Fiction
   claims, a few pieces per room (some personal experiences, some marked
   "Editor's pick"). Tags appear as filters once a piece using them is
   published.
6. **Account deletions.** Members request deletion from their account page;
   the privacy policy promises it within 30 days. Delete from
   `/admin/deletions` (admin role), or on the server:

   ```bash
   python scripts/delete_members.py one@example.com two@example.com   # preview
   python scripts/delete_members.py --file emails.txt --apply         # delete
   ```
7. **Email (Brevo, free plan: 300 a day).** In Brevo, add `infinityden.com`
   under Senders, Domains & Dedicated IPs → Domains, and add the records it
   shows in GoDaddy's DNS (the Brevo code, DKIM, and DMARC with `p=none`).
   GoDaddy adds `.infinityden.com` to names itself, and a domain must have only
   one SPF and one DMARC record. Once the domain shows as authenticated, create
   an SMTP key under SMTP & API and put it in `.env` as above. To check, use
   "Forgot your password?" on the site with your own account. If the server
   can't connect, the host may block port 587: set `SMTP_PORT=2525`.
8. **After launch.** Turn on HSTS in nginx once the site will only ever be
   served over HTTPS.

## Development Notes

- Keep routes focused on request and response handling.
- Put business rules and database interaction in services.
- Use reusable templates for repeated UI.
- Add Pydantic schemas for validation as API features are introduced.
- Keep secrets in `.env`, keep `.env.example` safe to commit, and document new environment variables in both places.

## Verification

Basic import check:

```bash
python -m compileall app scripts
```

Run the tests (they need no database):

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

Run the local server:

```bash
python run.py
```
