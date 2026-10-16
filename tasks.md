# TASKS.md

# INFINITY DEN TASK TRACKER

Progress against `vision.md`. Admin-specific work is tracked in `admin.md`.

---

# CURRENT STATUS

## Current Phase
- [x] Foundation (publishing platform)
- [x] Product vision documented (`vision.md`)
- [ ] Phase 1 — The foundation
- [ ] Phase 2 — Interaction
- [ ] Phase 3 — Community growth

## Current Focus
- [ ] `feature/fact-or-fiction`

---

# FOUNDATION (DONE)

Built before the current vision; kept and reused.

- [x] FastAPI app, settings, logging, centralized error handling, health check
- [x] MongoDB connection and indexes
- [x] Base layout, navbar, footer, reusable components
- [x] Article system: model, schemas, CRUD APIs, pagination, filtering, sorting
- [x] Article pages: listing, detail, related articles, breadcrumbs, read time, sharing
- [x] Categories and tags: models, APIs, listing and detail pages, filtering
- [x] Search: API, page, keyword search, filters, pagination
- [x] Newsletter: API, form, validation, duplicate prevention
- [x] Write-for-us pitch form and submission API
- [x] Admin: JWT auth, roles, CSRF, dashboard, article editor, category, submission, and user management
- [x] SEO: meta title/description, OpenGraph, Twitter cards, canonical URLs, breadcrumb schema

---

# PHASE 1 — THE FOUNDATION

Goal: valuable even with a small community. Work through these branches in
order; each assumes the previous ones are merged.

## 1. `refactor/remove-sponsored-and-businesses`
- [x] Remove the businesses model, service, API, admin page, homepage partial, and seed script
- [x] Remove `is_sponsored` / `sponsor_name` and the sponsored rail, notice, and filters
- [x] Remove the Business / Tech / Food / Travel fallback content
- [x] Verify the homepage and admin still render

## 2. `feature/knowledge-rooms`
- [x] Point `MONGODB_DB_NAME` at a development database before reseeding
- [x] Add `subtitle` to categories (model, schema, admin form)
- [x] Replace news/guide/review with article/experience/perspective
- [x] Add `is_speculative` and format labels on cards and article pages
- [x] Add `sources` to articles; show them on the article page
- [x] Seed the six launch rooms from `vision.md`
- [x] Make `/categories/{slug}` the canonical room page; point nav and cards to it
- [x] Rebuild the navigation for rooms (name + subtitle); destinations join as their branches ship

## 3. `feature/member-accounts`
- [x] Users model, schemas, and indexes
- [x] Sign up, log in, log out, reusing existing hashing and JWT utilities
- [x] Rate-limit login and sign-up (and admin login)
- [x] Public contributor profile at a username URL
- [x] Link articles to `author_id`

## 4. `feature/member-publishing`
- [x] Render article markdown server-side (escape-first renderer in `app/utils/markdown.py`, mirrors the editor preview)
- [x] Member editor at `/write` (title, summary, room, format, tags, sources; no cover images in Phase 1)
- [x] `pending_review` status and review queue in admin, with `review_note`
- [x] Human Library page at `/experiences` with writing prompts
- [x] Retire the public pitch form (old pitches stay readable in admin)
- [x] Check that unsafe HTML is not rendered

## 5. `feature/question-of-the-day`
- [x] `daily_questions` and `responses` models, schemas, and indexes
- [x] Admin: create and schedule questions; feature and hide responses
- [x] `/questions` page: today's question, featured responses, past questions
- [x] Members respond as a thought, answer, story, or researched answer

## 6. `feature/fact-or-fiction`
- [ ] `quiz_items` model, schema, and admin management
- [ ] `/play` page: answer, reveal the explanation, link to the deeper article
- [ ] Reusable Fact or Fiction card for the homepage

## 7. `feature/homepage-rebuild`
- [ ] New visual identity: palette, typography, room card style
- [ ] Homepage sections in the order given in `vision.md`
- [ ] Remove the static "live" stats card
- [ ] Real cover images; no placeholder SVGs on published content
- [ ] Verify at 375px, 768px, 1024px, 1440px

## 8. `feature/comments-bookmarks`
- [ ] Comments on articles
- [ ] Bookmarks with a saved-items page
- [ ] Reports on articles, responses, and comments; admin queue to hide or dismiss

## Platform items for Phase 1
- [ ] Generate `sitemap.xml`
- [ ] Generate `robots.txt`
- [ ] Add article schema markup
- [ ] Add organization schema
- [ ] Add a favicon
- [x] Prevent XSS in all member-generated content
- [ ] Validate all inputs; prevent NoSQL injection
- [x] Add a minimal test setup (`pytest`, `tests/`)
- [ ] One check per feature (ongoing)

---

# PHASE 2 — INTERACTION

- [ ] Debate Den with separate clarity / evidence / reasoning ratings
- [ ] More Arcade games: One-Minute Quiz, Guess the Connection, Daily Brain Spark
- [ ] Contributor reputation based on meaningful participation
- [ ] Follow rooms and writers
- [ ] Perspective Switch
- [ ] Related-idea recommendations
- [ ] Block members
- [ ] Visible corrections on articles

---

# PHASE 3 — COMMUNITY GROWTH

- [ ] Idea Web and Reading Trails
- [ ] Open Question Board
- [ ] Community research projects and curated collections
- [ ] My Curiosity Map and personalized discovery
- [ ] Live discussions or challenges, if members want them

---

# PLATFORM BACKLOG

Carried over from the foundation; pick up when needed.

## Performance
- [ ] Optimize MongoDB queries and reduce unnecessary DB calls
- [ ] Lazy load images
- [ ] Optimize CSS and JS loading
- [ ] Compress images

## Deployment
- [ ] Production settings and environment variables
- [ ] Static asset serving
- [ ] Production MongoDB
- [ ] Deploy, domain, HTTPS, monitoring

## Accounts
- [ ] Password reset by email (needs an email-sending service)
- [ ] Move rate-limit counters out of process memory before running several workers

## CMS
- [ ] Member cover images (with the media library)
- [ ] Scheduled publishing
- [ ] Media library

## Analytics
- [ ] Article analytics
- [ ] Popular articles section

---

# DEVELOPMENT NOTES

## Workflow Rules
- Follow `instructions.md`; build only what the current phase of `vision.md` includes
- One focused branch per task, merged to `main` through a pull request
- Test before marking tasks complete
- Prefer reusable architecture
