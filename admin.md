# ADMIN.md

# ADMIN SYSTEM ROADMAP

This file tracks admin-specific functionality, security, and workflow improvements.
Use it alongside `tasks.md`; keep this file focused on the admin area only.

---

# CURRENT ADMIN STATUS

## Completed
- [x] Admin schema/model
- [x] Password hashing
- [x] JWT login API
- [x] Admin login page
- [x] Protected admin dashboard routes
- [x] Admin dashboard shell
- [x] Admin sidebar and topbar
- [x] Dashboard metrics
- [x] Article management table
- [x] Article create/edit form
- [x] Article publish action
- [x] Article draft action
- [x] Article featured toggle
- [x] Category management UI
- [x] Category create/update/delete UI
- [x] Submission review UI
- [x] Submission accept/reject/reviewing actions
- [x] Command-line admin creation script

---

# IMMEDIATE PRIORITY

## 1. Secure Admin Mutations
- [x] Protect article create/update/delete APIs with admin authentication
- [x] Protect category create/update/delete APIs with admin authentication
- [x] Protect tag create/update/delete APIs with admin authentication
- [x] Keep public read APIs available without login
- [x] Return consistent `401` responses for unauthenticated admin writes
- [x] Return consistent `403` responses for insufficient role access

## 2. CSRF Protection
- [x] Add CSRF token generation for admin sessions
- [x] Render CSRF token into admin pages
- [x] Send CSRF token with admin fetch requests
- [x] Validate CSRF token on POST/PATCH/DELETE admin routes
- [x] Keep login/logout behavior safe and predictable

## 3. Role Permissions
- [x] Define role capabilities for `admin`
- [x] Define role capabilities for `editor`
- [x] Restrict admin-user management to `admin`
- [x] Restrict destructive actions if needed
- [x] Add role checks as reusable dependencies

---

# ADMIN USER MANAGEMENT

## Admin Accounts
- [ ] Create admin user listing page
- [ ] Create admin user form
- [ ] Add create admin API
- [ ] Add update admin role API
- [ ] Add change password API
- [ ] Add disable/deactivate admin API
- [ ] Prevent deleting or disabling the last admin
- [ ] Show created/updated timestamps for admin users

## Current Temporary Workflow
- [x] Create admins with `scripts/create_admin.py`

Run:

```bash
venv/bin/python scripts/create_admin.py
```

---

# ARTICLE EDITOR IMPROVEMENTS

## Editor Experience
- [ ] Add markdown editor or rich text editor
- [ ] Add preview mode
- [ ] Add draft autosave
- [ ] Add unsaved changes warning
- [ ] Add editor validation summary
- [ ] Improve tag entry UX
- [ ] Improve category selector UX

## Publishing Workflow
- [ ] Add scheduled publishing
- [ ] Add publish confirmation
- [ ] Add unpublish confirmation
- [ ] Add archive action
- [ ] Add publish status history

## SEO Tools
- [ ] Add SEO preview
- [ ] Add title length guidance
- [ ] Add description length guidance
- [ ] Add canonical URL editor if needed
- [ ] Add OpenGraph image selector

---

# ADMIN LISTING IMPROVEMENTS

## Articles
- [ ] Add search by title/slug
- [ ] Filter by status
- [ ] Filter by category
- [ ] Filter by featured state
- [ ] Add pagination
- [ ] Add bulk actions
- [ ] Add safe delete confirmation modal

## Categories
- [ ] Add search
- [ ] Add pagination
- [ ] Show article count per category
- [ ] Prevent deleting categories used by articles unless confirmed

## Submissions
- [ ] Filter by status
- [ ] Add pagination
- [ ] Add submission detail view
- [ ] Create draft from accepted submission
- [ ] Store review notes

---

# MEDIA LIBRARY

## Image Management
- [ ] Add media upload API
- [ ] Add media listing page
- [ ] Add image picker for article cover images
- [ ] Validate image type and size
- [ ] Generate thumbnails
- [ ] Add image alt text fields

---

# AUDIT AND HISTORY

## Activity Tracking
- [ ] Track who created articles
- [ ] Track who updated articles
- [ ] Track who published/unpublished articles
- [ ] Track submission review actions
- [ ] Add admin activity log page

---

# SECURITY HARDENING

## Backend
- [ ] Validate all admin inputs
- [ ] Prevent NoSQL injection in admin filters
- [ ] Improve JWT secret checks at startup
- [ ] Add secure cookie settings for production
- [ ] Add rate limiting for admin login
- [ ] Add account lockout or cooldown after repeated login failures

## Frontend
- [ ] Avoid injecting unsafe HTML into admin pages
- [ ] Sanitize preview content
- [ ] Keep admin pages `noindex`
- [ ] Avoid exposing sensitive admin-only data in public responses

---

# NICE TO HAVE

## Dashboard
- [ ] Add chart for publishing activity
- [ ] Add popular articles widget
- [ ] Add recent admin activity widget
- [ ] Add quick links for common actions

## Workflow
- [ ] Add content checklist before publish
- [ ] Add internal notes for articles
- [ ] Add reviewer assignment
- [ ] Add editorial calendar view
