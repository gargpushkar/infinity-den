# PROJECT INSTRUCTIONS

## Project Overview

This project is a modern content publishing and content marketing platform.

The platform supports:
- Articles/blog posts
- Categories
- Tags
- Featured content
- Search
- Newsletter subscriptions
- Write-for-us submissions
- Admin dashboard
- SEO-friendly pages
- Responsive frontend

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

## ALWAYS
- use modular architecture
- use reusable templates/components
- use environment variables
- use async routes where beneficial
- use proper error handling
- write scalable code
- maintain clean naming conventions

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
│   ├── controllers/
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
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   ├── images/
│   │   └── fonts/
│   │
│   └── admin/
│
├── requirements.txt
├── .env
├── .gitignore
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

## MongoDB Collections

### articles

Fields:

- title
- slug
- excerpt
- content
- cover_image
- author
- category_id
- tags
- is_featured
- status
- seo_title
- seo_description
- created_at
- updated_at
- published_at
- views

### categories

Fields:

- name
- slug
- description
- image

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

### admins

Fields:

- username
- password_hash
- role

---

# FRONTEND RULES

## UI Style

The design should be:

- modern
- minimal
- spacious
- responsive
- clean typography
- soft rounded corners
- card-based

## Layout

Homepage should contain:

- Navbar
- Hero/tagline section
- Featured articles carousel
- Latest articles grid
- Category sections
- Write-for-us CTA
- Footer

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

Always follow this order:

1. Project structure
2. App initialization
3. MongoDB setup
4. Base templates
5. Homepage
6. Reusable components
7. Public article system
8. Categories/tags
9. Search
10. Newsletter
11. Write-for-us
12. Admin auth
13. Admin dashboard
14. SEO optimization
15. Performance improvements

Do NOT skip steps.

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

Build MVP content publishing platform.

Priority:

- Clean architecture
- Responsive frontend
- SEO-ready structure
- Admin management
- Scalability

---

# INITIAL TASKS

Start by:

1. Creating project structure
2. Setting up FastAPI app
3. Setting up MongoDB connection
4. Creating base templates
5. Creating homepage
6. Building reusable navbar/footer
7. Creating responsive homepage layout
8. Creating article card component

Proceed incrementally.
