# Radilox

A Django app for uploading videos, images and songs to a public profile,
backed by Cloudinary storage. Files upload directly from the browser to
Cloudinary (not proxied through Django) for speed, songs get a full
"Boom Player" experience with a live equalizer and lock-screen controls,
and every detail page autoplays into the next video or song so you're
never dumped back to the feed. The look is a light, airy "milky blue
glass" theme — frosted, semi-transparent cards floating over a soft blue
gradient canvas with slowly drifting color blobs, carrying Cloudinary's
saturated blue-violet brand gradient as the accent color.

## Features

- **Authentication via django-allauth**, including **Google sign-in** —
  username/email/password signup still works too
- Public profile pages (`/u/<username>/`) showing everything a user has
  uploaded, with avatar, bio, and website link
- **Direct-to-Cloudinary uploads** — the file never touches the Django
  server, it streams straight from your browser to Cloudinary with a real
  progress bar, so publishing is fast even on large video files
- Upload videos, images, **or songs**, with a redesigned drag-and-drop
  uploader (songs support optional cover art)
- Animated **hero slideshow** on the feed, cross-fading through the
  community's latest videos and images
- Global feed with All / Videos / Images / Songs filter tabs
- Every detail page shows **"More from this creator"** and **"Discover
  more"** sidebars, and **autoplays into the next item** when the current
  one ends — no need to go back to the feed to keep watching/listening
- **Comments post over AJAX** — playback never stops or resets just
  because you typed a comment
- Songs get the full **Boom Player**: circular spinning cover art, a live
  Web-Audio equalizer visualizer, a 3-band bass/mid/treble EQ you can
  drag while it plays, and **Media Session integration** so the track
  title, artist, and play/pause/next/previous controls show up on your
  phone's lock screen / notification shade while Radilox is in the
  background
- **Like** (AJAX heart toggle, one like per user per item)
- **Share** (copies a link to the clipboard and tracks a share count)
- **Download** (forces a real file download via Cloudinary's attachment
  flag and tracks a download count)
- View / like / comment / download counters shown on every card
- Owners can delete their own uploads
- Django admin for moderation
- When someone signs up with Google, their name and profile photo are
  pulled across automatically (best-effort — never blocks signup if it fails)

## Stack

- Django 5
- `django-allauth` for authentication, including Google OAuth
- `cloudinary` + `django-cloudinary-storage` for media hosting
- SQLite for the database (swap for Postgres in production if you like)
- No JS framework — plain templates + one small stylesheet

## Setup

1. **Clone & create a virtualenv**

   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Get Cloudinary credentials**

   Sign up free at https://cloudinary.com, then from the dashboard copy your
   Cloud name, API key, and API secret.

3. **Create an unsigned upload preset (this is what makes uploads fast)**

   Uploads go straight from the browser to Cloudinary — Django never
   touches the file bytes — which is what an "unsigned upload preset"
   enables:

   1. In the Cloudinary dashboard, go to **Settings → Upload → Upload
      presets → Add upload preset**
   2. Set **Signing Mode** to **Unsigned**
   3. Give it a name (e.g. `radilox_unsigned`) — you'll put this in `.env`
   4. Save

   Without this, the upload page still renders but shows a friendly error
   instead of silently failing when someone tries to publish.

4. **Get Google OAuth credentials (for "Continue with Google")**

   1. Go to https://console.cloud.google.com/apis/credentials
   2. Create a project (or pick an existing one)
   3. Click **Create Credentials → OAuth client ID**
      - Application type: **Web application**
      - Authorized JavaScript origins: `http://localhost:8000` (and your
        production domain later)
      - Authorized redirect URIs:
        `http://localhost:8000/accounts/google/login/callback/`
   4. Copy the generated **Client ID** and **Client secret**
   5. If prompted, configure the OAuth consent screen (External is fine for
      testing — add yourself as a test user while it's unpublished)

   If you skip this step, the "Continue with Google" button will still
   appear (since the provider is registered via settings), but clicking it
   will fail against Google with invalid-client errors until you fill in
   real credentials. Username/password auth works regardless.

5. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env`:

   ```
   SECRET_KEY=<generate one, e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`>
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   CLOUDINARY_CLOUD_NAME=your-cloud-name
   CLOUDINARY_API_KEY=your-api-key
   CLOUDINARY_API_SECRET=your-api-secret
   CLOUDINARY_UPLOAD_PRESET=radilox_unsigned
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   ```

6. **Migrate & run**

   ```bash
   python manage.py migrate
   python manage.py createsuperuser   # optional, for /admin/
   python manage.py runserver
   ```

   Visit `http://127.0.0.1:8000/`. The site listens on port 8000 by
   default — if you registered the Google redirect URI against a
   different port, keep them in sync.

## Authentication

Auth is handled entirely by `django-allauth`:

- `/accounts/login/`, `/accounts/signup/`, `/accounts/logout/` — standard
  username/email/password flows, restyled to match the site theme
- `/accounts/google/login/` — kicks off Google OAuth; allauth handles the
  callback at `/accounts/google/login/callback/` automatically
- Profile pages live at `/u/<username>/` (moved off `/accounts/` since
  allauth owns that prefix) and `/u/me/edit/` for editing your own

Every allauth page (login, signup, password reset, etc.) is themed via
template overrides in `templates/allauth/` — see **Design notes** below.
The `accounts.Profile` model still auto-creates via a `post_save` signal on
`User` regardless of whether the user signed up with a password or Google.

## How uploads work

Uploads are **direct-to-Cloudinary from the browser** — Django is never in
the file's path:

1. You pick a file in the redesigned drag-and-drop uploader
   (`templates/media_hub/upload.html`)
2. The browser's JS (`XMLHttpRequest`, for real progress events) posts the
   file straight to `https://api.cloudinary.com/v1_1/<cloud>/auto/upload`
   using the **unsigned upload preset**, with a live progress bar
3. Cloudinary responds with a `public_id`, `resource_type`, `format`, and
   `version`
4. That small JSON payload — not the file — gets posted to
   `media_hub:finalize_upload`, which creates the `Media` row by pointing
   its `CloudinaryField` at the already-uploaded resource

This is what makes uploading noticeably faster than the old flow: the file
is transferred once (browser → Cloudinary) instead of twice (browser →
Django → Cloudinary). `media_hub/context_processors.py` exposes the cloud
name, preset, and upload URL to templates (the API secret is never sent to
the browser). `finalize_upload` validates every field it's given (media
type, and that `public_id`/`resource_type`/`format`/`version` look like
real Cloudinary tokens) before creating anything.

Profile avatars still go through Django's own `CloudinaryField` upload path
(via `DEFAULT_FILE_STORAGE = cloudinary_storage.storage.MediaCloudinaryStorage`)
since that form is small and infrequent — the speed optimization only
mattered for the large video/audio files on the main upload flow.

## Playback: autoplay, sidebars, and the Boom Player

Every detail page (`media_hub/views.py:detail`) computes two lists —
**More from this creator** and **Discover more** — filtered to the same
media type as the item you're viewing, and passes their combined IDs to
the template as an "up next" queue. What happens with that queue differs
by media type:

- **Video**: the `<video>` element's `ended` event navigates to the first
  sidebar item's URL — one automatic step, no trip back to the feed
- **Audio**: this is the flagship experience — the **Boom Player**. It
  never navigates away. `ended` (and the Next button) fetch
  `media_hub:track_json` for the next queued track, swap the `<audio>`
  element's `src` in place, and keep playing. Because it's the same
  `<audio>` DOM element throughout, the Web Audio graph built on top of it
  (equalizer + visualizer) survives the track change too
- **Images**: no autoplay concept, but you still get both sidebars to keep
  browsing

**Comments post over `fetch()`**, not a form submission that reloads the
page — so whatever's playing in the `<video>`/`<audio>` element just
keeps playing while you comment.

**The Boom Player** (audio detail pages only) is a small self-contained
Web Audio setup, all in `templates/media_hub/detail.html`:

- A `MediaElementAudioSourceNode` pulled from the `<audio>` tag feeds
  three chained `BiquadFilterNode`s — `lowshelf` (bass), `peaking` (mid),
  `highshelf` (treble) — into an `AnalyserNode`
- The three EQ sliders drive `filter.gain.value` live while the track plays
- The analyser's frequency data drives 40 animated bars (`requestAnimationFrame`)
  for the equalizer visualizer
- `navigator.mediaSession` is populated with the track's title, artist, and
  cover art, with `play`/`pause`/`previoustrack`/`nexttrack`/`seekto`
  action handlers wired to the same controls — this is what makes the
  track, and working prev/next/play/pause buttons, show up on your phone's
  lock screen or notification shade while you're in another app

**Scope note, stated plainly:** because Radilox is a normal server-rendered
Django app (not a single-page app), navigating to a *different* page still
does a full page load, which unavoidably stops playback — the in-place
swapping above only works because advancing to the next song deliberately
avoids a navigation. Media Session keeps a song alive in the background
tab/behind other apps, but a full SPA rewrite would be a much bigger
architectural change than this feature set required.

## Project layout

```
config/            Django settings, root urls (mounts allauth + accounts + media_hub)
accounts/           Profile model (1:1 with User), profile view/edit, Google-signup enrichment signal
media_hub/          Media/Like/Comment models, feed/upload/detail/like/comment/share/download/finalize_upload/track_json views, cloudinary_settings context processor
templates/          Theme templates — base.html + per-app templates + allauth/ overrides
static/css/         Single stylesheet — theme tokens live at the top of the file
```

## Design notes

The theme lives entirely in `static/css/style.css` — a light "milky blue
glass" look. Tokens are declared as CSS custom properties at the top:

- `--bg-1/2/3` — the soft blue-white gradient the whole page sits on,
  with four blurred, slowly-drifting color blobs (`.bg-orbs` in
  `base.html`) behind everything for movement
- `--surface` + `--glass-blur` — the frosted-glass fill
  (`rgba(255,255,255,0.58)` + `backdrop-filter: blur(18px) saturate(160%)`)
  used on the header, cards, buttons, form panels, and sidebars
- `--media-bg` — a near-black navy used *only* behind actual video/image/
  audio tiles, so content pops against the light glass chrome (this is
  intentional — video always looks better letterboxed on black, regardless
  of the site theme around it)
- `--cloud-blue` / `--cloud-violet` / `--cloud-sky` / `--cloud-pale` and
  `--gradient-brand` — Cloudinary's blue-violet identity lightened toward
  sky/pale blue, used on primary buttons, the logo mark, the active filter
  tab, the liked heart, avatar rings, and the hero gradient text

Signature elements: the drifting background orbs, frosted-glass cards
throughout, the animated hero slideshow cross-fading through the
community's own uploads, and the Boom Player described above.

allauth's own pages are themed by overriding its template "elements"
system rather than each page individually — `templates/allauth/layouts/base.html`
supplies the shared header/footer/CSS shell (including the background
orbs), and `templates/allauth/elements/` restyles its buttons, form
fields, and social-provider links so every allauth-rendered page (login,
signup, password reset, Google connect, etc.) matches the rest of the site
automatically.

## Deploying

This is a standard Django app — deploy it anywhere Django runs (Render,
Railway, Fly.io, a VPS with gunicorn + nginx, etc.). Since media lives on
Cloudinary, you don't need persistent disk for uploads; you do still want a
real database (Postgres) in production instead of SQLite.

Static files are served via `whitenoise` in production — add
`whitenoise.middleware.WhiteNoiseMiddleware` to `MIDDLEWARE` (right after
`SecurityMiddleware`) and run `python manage.py collectstatic` before deploying
if you go that route.
