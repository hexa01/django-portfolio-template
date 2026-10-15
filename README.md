# Django portfolio and blog for developers

An open-source developer portfolio template built with Django: projects with architecture diagrams and design
decisions, a Markdown technical blog with code highlighting, resume, about and contact pages. Server-rendered,
plain HTML/CSS/JS, no build step, deployable with Docker.

Content is managed in Django's admin, and optionally by AI agents through MCP (see [AI agent editing](#ai-agent-editing)).

Built by [Sushan Poudel](https://sushanpoudel.com). Use it for your own site.

## Features

- **Pages:** home (hero with an animated architecture panel), about, projects, blog, resume (with PDF download),
  contact form (honeypot and rate limit, saved to admin).
- **Projects:** Markdown case studies (problem, approach, result), "key decisions" (decision, why, trade-off) and
  diagrams. SVG diagrams are sanitised and follow the light/dark theme.
- **Blog:** Markdown with syntax highlighting, an "On this page" list built from headings, categories, tags,
  full-text search (PostgreSQL), drafts and scheduled posts, an advisory editorial checklist, and cross-posting
  support (canonical link to the original, e.g. Medium).
- **Admin as the CMS:** a Markdown toolbar with live preview, per-page SEO titles and descriptions, image resizing.
- **Search:** Ctrl/Cmd+K site search across projects and posts.
- **SEO:** sitemap, robots.txt, RSS (readable in browsers), structured data (Person, WebSite, BlogPosting,
  breadcrumbs), generated social preview cards, share links, and a switch to hide the site from search engines
  until it's ready.
- **Design:** dark-first with a light theme, three colour themes in plain CSS, IBM Plex fonts (self-hosted),
  view transitions between pages, works without JavaScript, respects reduced motion.
- **AI agents:** posts, projects, the profile and page texts are editable by Claude Code and other MCP clients,
  with revocable keys, drafts by default and no deletes (see [AI agent editing](#ai-agent-editing)).

## Stack

Python 3.12, Django 5.2, PostgreSQL 16, Docker Compose, Gunicorn, WhiteNoise, Nginx (production),
[django-agent-content](https://pypi.org/project/django-agent-content/) for agent editing.
Dependencies are managed with Poetry; the server installs from `requirements.txt`.

## Run it locally

Requires Docker.

```bash
git clone <this repository> portfolio && cd portfolio
cp .env.example .env               # then set SECRET_KEY and POSTGRES_PASSWORD
docker compose up                  # http://127.0.0.1:8055 (runserver, auto-reload, code mounted)
docker compose exec web python manage.py createsuperuser
```

Open http://127.0.0.1:8055/admin/ and replace the starter content:

1. **Site profile:** name, role, highlights (one per line), tagline, availability, about text, photo, logo,
   resume PDF, social links. The initials of your name become the logo and the browser tab icon until you upload one.
2. **Focus areas**, **Experiences**, **Education**, **Skill groups:** the home and resume pages.
3. **Projects** and **Posts:** your work and writing.
4. **Page texts:** optional SEO titles, intros and search descriptions for About, Projects, Blog, Resume and
   Contact. Empty fields fall back to sensible defaults.

Sections without content hide themselves.

## Customise the look

Colours live in one file per theme: `static/css/themes/forest.css` (default), `paper.css`, `graphite.css`. Each
defines every colour for dark mode (`:root`) and light mode (`[data-theme="light"]`). To make your own, copy one,
change the values and set `SITE_THEME` in `config/settings.py`. Fonts, type sizes and spacing are in
`static/css/tokens.css`; no other CSS file contains a colour. A system check stops the site if the theme file is
missing, and tests check that every theme defines all colours with readable contrast.

## Configuration

All settings come from `.env` (see `.env.example`):

| Setting | Meaning |
|---|---|
| `SECRET_KEY` | Django's secret key: long and random in production |
| `DEBUG` | `True` locally, `False` in production (enables the HTTPS settings) |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | your domain(s) |
| `SITE_INDEXABLE` | `False` hides the site from search engines (robots.txt and `noindex`) |
| `SECURE_HSTS_SECONDS` | HSTS duration; start low, raise to a year once HTTPS works |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | the database; Docker builds `DATABASE_URL` from them |
| `WEB_PORT` | host port the site listens on (127.0.0.1 only) |
| `APP_UID`, `APP_GID`, `GUNICORN_WORKERS` | production container user and worker count |

## Deploy

Production runs `docker-compose.server.yml` (Gunicorn, migrations on start, static files built into the image)
behind Nginx on the host, which handles HTTPS and serves uploads.

```bash
git clone <this repository> /path/to/project && cd /path/to/project
cp .env.example .env               # fill in the production values at the bottom of the file
mkdir -p media
docker compose -f docker-compose.server.yml up -d --build
docker compose -f docker-compose.server.yml exec web python manage.py createsuperuser
```

Then install `deploy/nginx.conf` as a site (replace `example.com`, `/path/to/project` and the port), and add HTTPS
with Certbot: the steps are at the top of that file. Updating later is `git pull` and the same `up -d --build`.

Back up the database nightly with `deploy/backup.sh` (keeps 7 days):

```
15 3 * * * cd /path/to/project && ./deploy/backup.sh >> backups/backup.log 2>&1
```

To move content from one machine to another, dump the database (`pg_dump -Fc`), restore it with
`pg_restore --clean`, and copy the `media/` folder.

## AI agent editing

Optional. The site includes [django-agent-content](https://github.com/hexa01/django-agent-content), which lets MCP
clients edit content through [agent-content-mcp](https://github.com/hexa01/agent-content-mcp). What agents may edit
is set in each app's `agent_resources.py`. Without an API key, nothing is exposed.

To use it, create a key on the site, then register the MCP server (requires [uv](https://docs.astral.sh/uv/)):

```bash
docker compose exec web python manage.py agent_content_key --label "my laptop"

claude mcp add agent-content \
  -e AGENT_CONTENT_URL=https://example.com/api/agent/ -e AGENT_CONTENT_KEY=ac_... \
  -- uvx agent-content-mcp
```

The tools are generated from what this site registers; `/mcp` in Claude Code lists them. See the two packages'
READMEs for more on how it works.

## Tests

```bash
docker compose exec web python manage.py test
```

## Project layout

```
config/      settings, URLs
core/        home, about, resume, page texts, SEO helpers, preview cards, health check
projects/    projects and key decisions
blog/        posts, categories, tags, search, RSS
contact/     contact form and rate limiting
templates/   base layout, partials, per-app templates, error pages
static/      css (tokens, themes), js, fonts
deploy/      Nginx template and backup script
```

## License

MIT, see [LICENSE](LICENSE). The bundled IBM Plex fonts are under the SIL Open Font License
([`static/fonts/OFL.txt`](static/fonts/OFL.txt)).
