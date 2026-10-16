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
| Question Room | `/questions` |
| Human Library | `/experiences` |
| Curiosity Arcade | `/play` |
| Debate Den (Phase 2) | `/debates` |
| Member profile | `/members/{username}` |
| Join / sign in / sign out | `/join`, `/login`, `/logout` |
| Your account | `/account` |

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
- cover_image
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
- image
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

### daily_questions *(new)*

Curated by editors.

Fields:

- text
- slug
- intro
- category_id
- publish_date (the day it is Question of the Day; unique)
- status — `draft` | `published`
- created_at

### responses *(new)*

Fields:

- question_id
- user_id
- body
- kind — `thought` | `answer` | `story` | `researched`
- is_featured (set by editors; featured means insightful, not popular)
- status — `published` | `hidden`
- created_at

### comments *(new)*

Fields:

- article_id
- user_id
- body
- status — `published` | `hidden`
- created_at

### bookmarks *(new)*

Fields:

- user_id
- article_id
- created_at

Unique index on `(user_id, article_id)`.

### quiz_items *(new)*

Fact or Fiction claims.

Fields:

- claim
- is_true
- explanation
- article_slug (the deeper article the explanation links to)
- category_id
- status — `draft` | `published`
- created_at

### reports *(new)*

Fields:

- target_type — `article` | `response` | `comment`
- target_id
- reporter_id
- reason
- status — `open` | `resolved` | `dismissed`
- created_at

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
- soft rounded corners
- card-based content

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
- `sitemap.xml`
- `robots.txt`
- canonical URLs

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

- render markdown server-side with an allowlist; never pass member HTML through `| safe`
- rate-limit member writes (posts, responses, comments, reports) and login
- never expose member emails or password hashes in public pages or API responses
- every member-generated item can be reported by members and hidden by editors
- member contributions publish only after editorial review in Phase 1

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
