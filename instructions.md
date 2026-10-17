# PROJECT INSTRUCTIONS

## Project Overview

Infinity Den is a community knowledge platform: people discover ideas,
contribute lived experience, discuss questions, and learn through short games.

**Read `vision.md` before starting any feature.** It is the source of truth for
what the product is, which rooms and formats exist, and what belongs in each
phase. `tasks.md` tracks progress against it.

The platform is built on an existing publishing foundation:
- Articles, rooms (categories), and tags
- Search
- Newsletter subscriptions
- Admin dashboard with editorial review
- SEO-friendly pages
- Responsive frontend

Phase 1 adds member accounts, member publishing, the Question Room, the Human
Library, Fact or Fiction, comments, bookmarks, and moderation.

The architecture should prioritize:
- maintainability
- modularity
- scalability
- clean UI
- production readiness

---

# TECH STACK

## Backend
- FastAPI
- Python 3.12+
- MongoDB
- Motor or PyMongo
- JWT Authentication

## Frontend
- HTML5
- CSS3
- Bootstrap 5
- JavaScript
- jQuery
- Jinja2 templates

---

# IMPORTANT DEVELOPMENT RULES

## DO NOT
- generate extremely large files
- mix business logic inside routes
- duplicate template code
- create tightly coupled modules
- hardcode secrets
- overengineer
- introduce unnecessary libraries
- build features that are not in the current phase of `vision.md`

## ALWAYS
- use modular architecture
- use reusable templates/components
- use environment variables
- use async routes where beneficial
- use proper error handling
- write scalable code
- maintain clean naming conventions

---

# NAMING CONVENTION

Creative names are display text. Everything permanent is plain and descriptive.

- **Slugs and URLs** are descriptive and never change:
  `/categories/science`, not `/categories/cosmic-canvas`.
- **Code identifiers** are plain: `daily_question`, `response`, `quiz_item`,
  `debate` — never `spark_room`, `innerverse`, or `question_room`.
- **Creative names** (room names, feature names) live only in database fields
  (`name`, `subtitle`) and template labels, so a rename is a data or label
  change, never a refactor.

## URL structure

| Page | URL |
| --- | --- |
| Room | `/categories/{slug}` (the single canonical room page) |
| Room filtered by format | `/categories/{slug}?format=experience` |
| Article | `/articles/{slug}` (flat, never nested under a room) |
| Question Room | `/questions` (today's or latest), `/questions/{slug}` |
| Human Library | `/experiences` |
| Curiosity Arcade | `/play` (random claim), `/play/{slug}`, `/play/{slug}?answer=fact\|fiction` |
| Debate Den (Phase 2) | `/debates` |
| Member profile | `/members/{username}` |
| Join / sign in / sign out | `/join`, `/login`, `/logout` |
| Your account | `/account` |
| Write / edit your piece | `/write`, `/write/{id}` |
| Saved pieces | `/saved` |
| Report something | `/report?type=article\|response\|comment&id=…` |
| Comment on / save a piece (form posts) | `/articles/{slug}/comments`, `/articles/{slug}/bookmark` |

Do not add a second URL for the same page. Nav and cards link to the canonical
URL.

---

# PROJECT STRUCTURE

Follow this exact structure unless explicitly instructed otherwise.

```text
project_root/
│
├── app/
│   ├── main.py
│   │
│   ├── config/
│   │   ├── settings.py
│   │   └── constants.py
│   │
│   ├── database/
│   │   ├── mongodb.py
│   │   └── indexes.py
│   │
│   ├── routes/
│   │   ├── public/
│   │   ├── admin/
│   │   └── api/
│   │
│   ├── services/
│   │
│   ├── models/
│   │
│   ├── schemas/
│   │
│   ├── middleware/
│   │
│   ├── utils/
│   │
│   ├── templates/
│   │   ├── layouts/
│   │   ├── partials/
│   │   ├── pages/
│   │   └── components/
│   │
│   └── static/
│       ├── css/
│       ├── js/
│       ├── images/
│       └── fonts/
│
├── scripts/
├── requirements.txt
├── .env
├── .gitignore
├── vision.md
├── instructions.md
├── tasks.md
├── admin.md
├── README.md
└── run.py
```

# ARCHITECTURE RULES

## Routes

Routes should:

- only handle request/response
- call service layer
- avoid database logic

## Services

Services should:

- contain business logic
- handle database interaction
- remain reusable

## Schemas

Use Pydantic schemas for:

- validation
- request models
- response models

## Templates

Use reusable partials/components:

- navbar
- footer
- article cards
- category pills
- pagination

---

# DATABASE RULES

Fields marked *(new)* do not exist yet; they are added by the Phase 1 branch
listed in `tasks.md`. Fields marked *(remove)* are deleted along with their
code and seed data.

## MongoDB Collections

### articles

Fields:

- title
- slug
- excerpt
- content (markdown, rendered and sanitized server-side)
- cover_image — optional upload; without one the page uses the generated cover
- author (display name)
- author_id *(new)* — `users._id`; null for editorial pieces
- category_id (room slug)
- tags
- article_format — `article` | `experience` | `perspective` *(values change from news/guide/review)*
- is_speculative *(new)*
- sources *(new)* — list of `{title, url}`; required for `article` format
- is_featured
- is_editors_pick
- status — `draft` | `pending_review` *(new)* | `published` | `archived`
- review_note *(new)* — editor feedback when a submission is sent back
- seo_title
- seo_description
- created_at
- updated_at
- published_at
- views
- is_sponsored, sponsor_name *(remove)*

### categories (rooms)

Fields:

- name (creative display name)
- subtitle *(new)* (descriptive subtitle, always displayed)
- slug (descriptive, permanent)
- description
- image — optional; without one the room uses its generated cover
- nav_order

### users

Members. Admins stay in the separate `admins` collection; reuse the existing
password hashing and JWT utilities rather than writing new ones.

- Members sign in with their email; the username only appears in profile URLs.
- Login tokens carry `kind: "member"` or `kind: "admin"`, and each side
  rejects the other's.
- Member sessions last `MEMBER_TOKEN_EXPIRE_DAYS` (30 by default); admin
  sessions last `AUTH_TOKEN_EXPIRE_MINUTES`.
- Passwords: at least 10 characters, no composition rules.
- Public pages and API responses never include email or password hash.

Fields:

- username (unique, used in profile URLs)
- display_name
- email (unique, never shown publicly)
- password_hash
- bio
- is_active
- created_at
- updated_at

### daily_questions

Curated by editors.

Fields:

- text
- slug (`YYYY-MM-DD-words`, fixed at creation)
- intro
- category_id
- publish_date — `"YYYY-MM-DD"` in `SITE_TIMEZONE` (default `America/New_York`); unique
- status — `draft` | `published` (a published question goes live on its date)
- created_at, updated_at

With no question scheduled for today, `/questions` shows the latest past one.

### responses

One per member per question (unique index); members can edit or delete it.

Fields:

- question_id
- user_id, author, author_username
- body (markdown subset; 500 characters for `thought`, 3,000 otherwise)
- kind — `thought` | `answer` | `story` | `researched`
- sources — required for `researched`
- is_featured (set by editors; featured means insightful, not popular)
- status — `published` | `hidden`
- created_at, updated_at

No votes or likes. Order: featured first, then newest.

### comments

Flat (no replies), oldest first, posted immediately. Members can delete their
own comments but not edit them in Phase 1. A hidden comment stays visible to
its author with a note.

Fields:

- article_id
- user_id, author, author_username
- body (markdown subset, up to 2,000 characters)
- status — `published` | `hidden`
- created_at, updated_at

### bookmarks

Fields:

- user_id
- article_id
- created_at

Unique index on `(user_id, article_id)`.

### quiz_items

Fact or Fiction claims.

Fields:

- claim
- slug (claim words plus a short random tail, fixed at creation)
- is_true
- explanation (markdown subset)
- article_slug — optional, must be a published article; the "Go deeper" link
- category_id
- status — `draft` | `published`
- created_at, updated_at

Answering is a plain link and nothing is stored: no per-visitor state and no
answer statistics in Phase 1. Never render the answer before the visitor
chooses.

### reports

Members report from `/report?type=…&id=…`; editors decide in `/admin/reports`.
One open report per member per item (reporting again updates it); members
cannot report their own work. Nothing changes publicly until an editor acts:
**Hide** sets a response or comment to `hidden` and archives an article, and
closes every open report on that item as `resolved`; **Dismiss** closes them
as `dismissed`.

Fields:

- target_type — `article` | `response` | `comment`
- target_id
- reporter_id
- reason — a key of `REPORT_REASONS` in `constants.py`
- detail — optional note, required when the reason is "Something else"
- status — `open` | `resolved` | `dismissed`
- created_at, updated_at, resolved_at, resolved_by

### tags

Fields:

- name
- slug

### newsletter_subscribers

Fields:

- email
- created_at

### article_submissions

Fields:

- name
- email
- topic
- content_idea
- status
- created_at

The public pitch form is retired once member publishing ships; keep the
collection readable in admin until existing submissions are handled.

### admins

Fields:

- username
- password_hash
- role

### businesses *(remove)*

Removed with its model, service, API, admin page, partial, and seed script.

---

# FRONTEND RULES

## UI Style

The design should feel:

- intellectually curious
- slightly mysterious
- modern
- human — not academic, not childish, not a news portal

Keep these qualities from the existing system:

- spacious, responsive layouts
- clean typography with a serif display face
- gently rounded corners (8px)
- card-based content, used sparingly

## Visual identity

The palette comes from the logo (`app/static/images/brand/`): colour runs from
Ink at the edge to Amber at the centre, "the deeper you go, the warmer the light".

| Token | Colour | Use |
| --- | --- | --- |
| Ink | `#171A2B` | Text, the header and footer, dark surfaces |
| Copper | `#C2562F` | Buttons, the logo, large type |
| Text copper | `#A8461F` | Links and small accent text (Copper on Ivory is only 4.2:1) |
| Amber | `#F2A33A` | Highlights; text only on dark backgrounds |
| Ivory | `#FBF7F0` | The page background |

- Every colour is a CSS token in `main.css`; night values live in `night.css`.
  Never write a colour literal in a component rule; night mode depends on it.
  `tests/test_colour_contrast.py` checks the text pairings in both modes.
- **Night mode** follows the visitor's device setting until they use the
  header switch, which stores `light` or `dark` in a `theme` cookie. The base
  layout reads the cookie and sets `night.css`'s `media`, so pages never flash
  the wrong mode.
- **Fonts:** Newsreader for headlines and reading text, Poppins for navigation,
  buttons, and labels. Regular and medium weights; no black weights, no
  all-caps labels.
- **Covers:** `app/utils/covers.py` draws one from the logo's 15° square for
  every article and room, served at `/covers/{room}/{slug}.svg`. Each room has
  its own pattern. An uploaded `cover_image` always wins. Bump `COVER_VERSION`
  when the drawing changes. Social previews never use SVG; pages without a
  photo fall back to `images/brand/og-default.png`.
- **Logo:** use the kit's files, never retype the wordmark. The header and
  footer are Ink in both modes and use the on-dark logo.
- **Motion:** content never waits on a scroll animation to appear. Respect
  `prefers-reduced-motion`.

Room cards and room navigation always show the subtitle next to the name.
Every contribution shows its format label (Researched, Personal experience,
Opinion, and Speculation when flagged).

Only label something "live" when it is backed by real-time data.

## Layout

The homepage follows the section order in `vision.md` → HOMEPAGE.

## Bootstrap Usage

- Use Bootstrap grid properly
- Prefer utility classes
- Avoid deeply nested layouts

## Mobile Responsiveness

- Mobile-first
- Responsive navbar
- Hamburger menu
- Responsive cards
- Proper spacing on smaller devices
- Desktop sidebars become compact cards on mobile

---

# TEMPLATE RULES

## Base Layout

Create:

- `base.html`
- `navbar.html`
- `footer.html`

All pages should extend `base.html`.

## Reusable Components

Create reusable:

- `article_card.html`
- `featured_article_card.html`
- `pagination.html`
- `category_badge.html`

---

# API RULES

## REST Standards

Use:

- proper status codes
- JSON responses
- validation
- pagination

## API Naming

Use:

- `/api/articles`
- `/api/categories`
- `/api/tags`
- `/api/questions`
- `/api/responses`
- `/api/comments`
- `/api/bookmarks`
- `/api/quiz-items`
- `/api/reports`

Avoid inconsistent naming.

---

# SEO REQUIREMENTS

Implement:

- SEO-friendly slugs
- meta tags
- OpenGraph tags
- `sitemap.xml` and `robots.txt` (`app/routes/public/seo.py`); add new public
  page types to `app/services/sitemap_service.py`, and new private paths to
  `PRIVATE_PATHS`
- canonical URLs
- JSON-LD: Article on article pages, Organization and WebSite on the homepage,
  breadcrumbs where they appear

The Content Security Policy (`app/middleware/security_headers.py`) allows
scripts and styles only from this site, jsDelivr, and Google Fonts. Keep
templates free of inline scripts and `style=""` attributes; add a host to the
policy rather than loosening it.

---

# SECURITY REQUIREMENTS

Implement:

- JWT auth
- password hashing
- environment variable protection
- CSRF protection where relevant
- XSS prevention
- NoSQL injection prevention
- input validation

## Member content

Member content is untrusted input. In addition to the above:

- render content with `app/utils/markdown.py`, which escapes first and only links http(s); never pass member HTML through `| safe`
- keep `app/utils/markdown.py` and `renderMarkdownPreview` in `main.js` in step (a test compares them)
- members can edit drafts and pieces awaiting review; published pieces are locked for them
- rate-limit member writes (posts, responses, comments, reports) and login
- never expose member emails or password hashes in public pages or API responses
- every member-generated item can be reported by members and hidden by editors
- member pieces (articles, experiences, perspectives) publish only after editorial review in Phase 1
- responses and comments post immediately; editors can hide them, and members can report them

---

# PERFORMANCE REQUIREMENTS

Implement:

- lazy-loaded images
- paginated article lists
- indexed MongoDB queries
- minimized frontend JS
- optimized DB access

---

# CODING STYLE

## Python

- use type hints
- follow PEP8
- prefer async where useful
- keep functions focused

## JavaScript

- modular JS files
- avoid inline JS
- use jQuery only where useful

## HTML

- semantic HTML
- reusable templates
- avoid duplicated structures

---

# DEVELOPMENT FLOW

Work through the Phase 1 branches in the order listed in `tasks.md`. Each
branch is one focused change; later branches assume earlier ones are merged.

Before reseeding or migrating data, point `MONGODB_DB_NAME` at a development
database. Seed scripts write directly to whichever database `.env` names.

---

# OUTPUT FORMAT RULES

For every task:

- mention files created
- mention files modified
- explain implementation briefly
- avoid unnecessary code dumps

---

# GIT RULES

Use a branch-based workflow for all implementation work.

## Branch Strategy

- Keep `main` stable, tested, and deployable.
- Do not commit feature or bug-fix work directly to `main` unless explicitly instructed.
- Create a new branch from the latest `main` for each task or tightly related group of changes.
- Use clear branch prefixes:
  - `feature/...` for new functionality
  - `fix/...` for bug fixes
  - `refactor/...` for cleanup without behavior changes
  - `chore/...` for project setup, docs, tooling, or maintenance
- Keep branches focused and small.
- Use meaningful commit messages.

Example:

```bash
git checkout main
git pull origin main
git checkout -b feature/article-system
git add .
git commit -m "Added article CRUD APIs"
git push -u origin feature/article-system
```

## Pull Request Flow

After every stable feature:

- run verification
- commit changes on the task branch
- push the branch
- open a pull request into `main`
- merge into `main` after review or verification
- start the next task from the updated `main`

Recommended next-task flow:

```bash
git checkout main
git pull origin main
git checkout -b feature/next-task
```

## Stacked Branches

Only create a new feature branch from another feature branch when the next task truly depends on unmerged work.

Example:

```text
main
  └── feature/article-model
        └── feature/article-api
```

Avoid stacked branches by default because they are harder to review, merge, and roll back.

---

# TESTING RULES

Before finalizing:

- verify imports
- verify routes
- verify template inheritance
- verify MongoDB queries
- verify responsiveness

Each new feature leaves at least one automated check for its core logic
(permissions, validation, or the main query). Member-content features also
check that unsafe HTML is not rendered.

---

# IMPORTANT PROMPT BEHAVIOR

When responding:

- prioritize maintainability
- prefer reusable code
- avoid hacks
- avoid unnecessary abstraction
- explain architectural decisions if significant

If uncertain:

- ask before making large architectural changes

---

# CURRENT DEVELOPMENT GOAL

Current goal:

Deliver Phase 1 of `vision.md`: a foundation that is valuable even with a small
community.

Priority:

- Remove features from the previous version of the site
- Rooms with subtitles and the new contribution formats
- Member accounts and member publishing with editorial review
- Question Room, Human Library, Fact or Fiction
- The new homepage and visual identity
