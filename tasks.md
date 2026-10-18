# TASKS.md

# INFINITY DEN TASK TRACKER

Progress against `vision.md`. Admin-specific work is tracked in `admin.md`.

---

# CURRENT STATUS

## Current Phase
- [x] Foundation (publishing platform)
- [x] Product vision documented (`vision.md`)
- [x] Phase 1 — The foundation (all branches merged)
- [ ] Phase 2 — Interaction
- [ ] Phase 3 — Community growth

## Current Focus
- [x] `feature/community-pages`
- [x] Password reset by email (`feature/password-reset`; Brevo over SMTP)
- [x] Brevo: domain authenticated in GoDaddy DNS; sending from dave@infinityden.com verified (inbox, SPF/DKIM/DMARC pass)
- [ ] On the server: SMTP settings, `MAIL_FROM`, `SITE_URL`, and the server's IP in Brevo's Authorised IPs
- [x] Email confirmation at sign-up (`feature/email-confirmation`): unconfirmed members can read and save but not take part; unconfirmed accounts expire after 7 days
- [x] Account deletion: members request it (account deactivated at once, deleted within 30 days); editors delete from `/admin/deletions` or `scripts/delete_members.py`, one or many emails at a time (`feature/deletion-requests`)
- [x] Emails to writers when an editor publishes their piece or sends it back with a note
- [ ] Newsletter: confirmed subscriptions, one-click unsubscribe, sending from admin (or reword the footer until then)
- [ ] Phase 2: the Debate Den, in four branches (below)

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
- [x] Member editor at `/write` (title, summary, room, format, tags, sources, cover image)
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
- [x] `quiz_items` model, schema, and admin management
- [x] `/play` page: answer, reveal the explanation, link to the deeper article
- [x] Reusable Fact or Fiction card for the homepage

## 7a. `feature/visual-identity`
- [x] Palette and night mode from the logo kit, as CSS tokens
- [x] Newsreader and Poppins; no black weights or all-caps labels
- [x] Ink header and footer with the logo; favicon and app icons
- [x] Remove the grid background and scroll fade-in
- [x] Quieter cards: room and format as text, no pills
- [x] Colour contrast check for day and night
- [x] Verify at 375px, 768px, 1024px, 1440px, day and night

## 7b. `feature/generated-covers`
- [x] Generated covers from the logo motif, one pattern per room
- [x] Uploaded covers override; no placeholder SVGs on published content
- [x] One branded preview image for social sharing

## 7c. `feature/homepage-rebuild`
- [x] Homepage sections in the order given in `vision.md` (Direction C)
- [x] Remove the static "live" stats card, carousel, and rails
- [x] Fact or Fiction answered in place on the homepage
- [x] Verify at 375px, 768px, 1024px, 1440px, day and night

## 8a. `feature/comments-bookmarks`
- [x] Comments on articles (flat, members delete their own)
- [x] Bookmarks with a saved-items page (`/saved`)

## 8b. `feature/reports`
- [x] Reports on articles, responses, and comments
- [x] Admin queue to hide or dismiss

## Platform items for Phase 1
- [x] Generate `sitemap.xml`
- [x] Generate `robots.txt`
- [x] Add article schema markup
- [x] Add organization schema
- [x] Add a favicon
- [x] Prevent XSS in all member-generated content
- [x] Validate all inputs; prevent NoSQL injection (audited; tests in `tests/test_seo_and_hardening.py`)
- [x] Security headers (CSP, framing, nosniff, referrer) and a 1 MB request cap
- [x] Fix the footer newsletter form; rate-limit signups; same reply for duplicates
- [x] Add a minimal test setup (`pytest`, `tests/`)
- [ ] One check per feature (ongoing)

## Launch readiness
- [x] Community guidelines, editorial policy, privacy policy, and terms (`/guidelines`, `/editorial-policy`, `/privacy`, `/terms`), linked from the footer and member forms
- [x] Visible corrections: editors add a dated correction note shown on the piece
- [x] Fonts served from this site; no requests to Google
- [ ] Add a governing-law clause to the terms once the business's country is confirmed
- [ ] Replace `CONTACT_EMAIL` with a site address (for example on infinityden.com)
- [ ] Rotate server logs, so they are kept for a short time as `/privacy` says

---

# PHASE 2 — INTERACTION

- [ ] Debate Den with separate clarity / evidence / reasoning ratings
  - [x] `feature/debate-motions`: editors set motions with a closing date; members post one argument per debate, for or against, with optional sources; posted at once, reportable, hideable, featurable; `/debates`, `/debates/{slug}`
  - [x] `feature/debate-rebuttals`: one level of replies to an argument (any confirmed member but its author; one per member per argument; 20–1,000 characters); reportable and hideable; folded after three
  - [x] `feature/debate-ratings`: clarity, evidence, and reasoning, 1–5 each; confirmed members, not your own; averages after 3 ratings, shown to members who rated and to everyone once the debate closes; never used for ordering; `/privacy` updated
  - [ ] `feature/debate-stances`: where you stand before and after reading, with an optional "why"; results (minds changed, no winner) shown once a debate closes; homepage Debate Den section; `/privacy` update
- [ ] More Arcade games: One-Minute Quiz, Guess the Connection, Daily Brain Spark
- [ ] Contributor reputation based on meaningful participation
- [ ] Follow rooms and writers
- [ ] Perspective Switch
- [ ] Related-idea recommendations
- [ ] Block members

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
- [x] Count rooms and tags in one grouped query instead of one per row; run independent lookups in parallel (`fix/page-speed`)
- [ ] Put the app server and the Atlas cluster in the same region
- [ ] Optimize MongoDB queries and reduce unnecessary DB calls (ongoing)
- [ ] Lazy load images
- [ ] Optimize CSS and JS loading
- [ ] Compress images

## Deployment
- [ ] Production settings and environment variables
- [ ] Static asset serving
- [x] Fresh production database: setup checklist in `README.md`, `scripts/create_launch_rooms.py`, tags registered on publish
- [ ] Production MongoDB (create it following the README)
- [ ] Run uvicorn with `--proxy-headers` behind the host, so the sitemap, robots.txt, and canonical links use https
- [ ] Turn on HSTS once the site is served only over HTTPS
- [x] API docs (`/docs`, `/openapi.json`) are off when `APP_ENV=production`
- [ ] Deploy, domain, HTTPS, monitoring
- [ ] Set `MEDIA_DIR` outside the checkout, back it up, and set nginx `client_max_body_size 6m`

## Accounts
- [x] Password reset by email: one-hour, single-use links; a reset signs out every other device
- [ ] Tighten DMARC to `p=quarantine` once emails arrive reliably
- [ ] Move rate-limit counters out of process memory before running several workers

## CMS
- [x] Member cover images: upload (re-encoded to WebP, metadata removed) or an https link; admin editor uploads too
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
