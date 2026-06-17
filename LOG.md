# Project Log — TimeTables Room Booking Web App

## 2026-06-12
- Session start. Reviewed memory log — both memories still relevant (explain commands first; dual GitHub accounts).
- Installed `openpyxl` (user site-packages) to read the spreadsheet.
- Analysed `Room bookings 2025-2026.xlsx`:
  - 52 weekly sheets (1st Sept 2025 → 24th Aug 2026) + 4 unused Sheet1-4.
  - Each sheet: Mon/Tue (rows 3-11), Wed/Thu (13-21), Fri (23-31), two day-grids side by side.
  - Columns = 30-min slots 09:00–16:30 plus "17:00+".
  - Rows = rooms: Learn 1 (60), Learn 2 (60), Learn 3 (60), Seminar Room 3 (40), ALL (60), Nickson, Johnson, Nuffield. From ~Feb 2026 extra rooms appear: Joint Masters Lecture Room, Collaborative Learning Room (CLR), Small Computer Room.
  - Cell values = course/activity codes (TROP7xx, DTM&H, Ad Hoc).
  - Excel cell comments hold who booked / who it's for (e.g. "Kate Doyle: booked for ...").
- Produced plan for web app (Flask + week-grid UI, importer for existing data).
- Daniel's decisions:
  1. Auth: Azure Enterprise App (Entra ID) — access controlled by app assignment; implement with MSAL Python.
  2. Hosting: Daniel has VMs; one already runs PostgreSQL → use PostgreSQL (SQLAlchemy; SQLite for local dev).
  3. Permissions: all signed-in users can create + edit bookings; NO delete for now.
  4. Recurring/repeat bookings: required.
- Final architecture agreed: Flask + SQLAlchemy + PostgreSQL + MSAL, server-rendered week grid. Build phases 1-6 defined (skeleton → importer → grid → booking/recurrence → auth → deploy).

### Build (same day) — phases 1-5 done
- Created: `config.py`, `wsgi.py`, `requirements.txt`, `app/` (`__init__.py`, `models.py`, `auth.py`, `routes.py`, templates, static), `import_spreadsheet.py`. Extended `.gitignore` for Python.
- Installed deps with `pip install --user` (no venv — avoids OneDrive syncing thousands of venv files).
- Models: Room, Booking, BookingSeries (weekly repeats), AuditLog. Conflict check = overlapping time range on same room/date.
- Auth: dual-mode — Entra ID via MSAL when AZURE_CLIENT_ID env var set (phase 5 code already in place), else dev name/email form. DB: PostgreSQL via DATABASE_URL env var, else local SQLite (instance/timetables.db).
- Permissions as agreed: signed-in users create/edit; NO delete route exists (DELETE returns 405). All creates/edits audited with before/after.
- Importer: parses all 52 weekly sheets, merges consecutive identical cells into bookings, pulls Excel comments into notes with comment author as booked_by. Found and normalised room-name typos in workbook (NicksonNuffield→Nuffield, 3 spellings of Collaborative Learning Room, Joint MSc→Joint Masters). Result: **1238 bookings, 11 rooms**, 0 duplicates.
- Smoke-tested via Flask test client: login gate, grid render, create, conflict rejection (409), weekly repeat (skips clashing dates and reports them), edit, delete blocked (405), search, audit rows. All passed. Test bookings removed afterwards; DB holds only imported data.
- Decision: repeat bookings that clash with existing bookings are skipped (and listed to the user) rather than failing the whole series.
- Decision: spreadsheet's "17:00+" column stored internally as 17:00–18:00.
- TODO next: Daniel to try the app locally; then phase 6 (deploy to VM + Postgres + Entra app registration).
- Daniel added `Assets/` (LSTM logo pack); added it to `.gitignore` at his request. Note: any logo used by the app must be copied into `app/static/` (committed) — pick an RGB PNG/SVG variant, not CMYK/EPS.

### Branding (2026-06-12)
- Sampled exact brand colours from the RGB sail PNGs: LSTM Red #DC002E, Burgundy #790033, Sand #F4F1DE.
- Copied downscaled logos into `app/static/`: `lstm_logo_white.png` (white Full Marque, top bar), `lstm_logo.png` (full-colour, login page), `favicon.png` (sails). Originals stay in gitignored `Assets/`.
- Restyled: burgundy top bar with red underline + white logo, LSTM Red primary buttons/today/slot-hover, sand table headers and page background. Installed Pillow (--user) for the resizing.
- Verified via test client: pages reference the logos and all static assets serve 200.

### POC deployment plan (2026-06-12)
- Daniel's decisions for the demo: Linux VM, dev-login form (no Entra yet), **SQLite — no DB server** (POC, must be demonstrable + linked on the "trackon" front page).
- Git state checked: all app code committed + pushed to `origin` = `https://lstm-git@github.com/lstm-git/TimeTables.git`, `main` level with `origin/main`. Working tree clean (Daniel commits this session's work in his own terminal).
- Key gotchas found:
  - `*.db` and `*.xlsx` are gitignored → a fresh clone has **no data**. Plan: copy the single `instance/timetables.db` to the VM (SQLite = one file). App auto-creates empty tables if absent.
  - `Assets/` was committed before the ignore rule was added, so the whole logo pack (CMYK/EPS/PDF + `__MACOSX`) is tracked in the repo — bloat, not breaking. Cleanup deferred. App only uses the 3 PNGs in `app/static/`.
- Wrote `DEPLOY.md`: clone → venv + requirements → scp the .db → SECRET_KEY env → systemd service running `waitress-serve --listen=0.0.0.0:8000 wsgi:app` → open port 8000 → link on trackon. Includes update procedure and POC caveats (dev-login = no real security, SQLite concurrency, no HTTPS).
- TODO: actual deployment is on the VM (no access from here). After demo: phase 6 hardening = Entra SSO + Postgres + nginx/HTTPS.

### VM deploy progress (2026-06-17)
- Path on VM: `/opt/trackon/timetables` (it's a sub-project of trackon). Cloned via HTTPS+PAT.
- venv + requirements installed on VM.
- Data transfer: VM is in a DMZ — inbound SSH/scp (port 22) blocked, so push-scp from Windows fails. VM has outbound HTTPS (it cloned from GitHub), so routed data **through the repo**: dumped SQLite to text `seed_data.sql` (262K, committed, NOT gitignored), pull on VM, rebuilt DB with stdlib `sqlite3.executescript`. VM confirmed 1240 bookings. Stripped one stray "test" booking before dumping.
- Reverse proxy: Daniel has nginx; chose to serve at **subpath** `http://<trackon-host>/timetables/` (not own hostname).
- Code changes for subpath (committed): `ProxyFix(x_for,x_proto,x_host,x_prefix)` in `app/__init__.py`; `window.APP_ROOT = request.script_root` in `base.html`; prefixed the 3 hardcoded JS paths (`/api/bookings`, `/week/`) in `grid.js` with APP_ROOT. nginx sends `X-Forwarded-Prefix /timetables`. Verified via test client: root mode = no prefix; with header = all links/static/JS prefixed.
- waitress binds `127.0.0.1:8000`; nginx faces the network. systemd unit `timetables.service` runs as `administrator`, EnvironmentFile `/etc/timetables.env` (SECRET_KEY set; DATABASE_URL/AZURE_* unset = SQLite + dev-login).
- DMZ note: inbound 8000 also likely blocked; reach via nginx on 80/443 — network team may need to permit it.
- nginx serves trackon on **443 only** (`/etc/nginx/sites-available/trackon`, server_name trackon.lstmed.ac.uk). Early curl tests failed only because they used http/port-80 (not served). timetables location blocks are correctly inside the 443 server. Real URL: `https://trackon.lstmed.ac.uk/timetables/`.
- Bug fixed: post-login redirect dropped the `/timetables` prefix (landed on trackon homepage). `login_required` captured `next=request.full_path` which excludes script_root → now `request.script_root + request.full_path`. Verified: after-login lands in app; local dev unaffected.
- Naming clarified: **"Room Bookings" is an existing Trackon feature for Meeting Rooms** — distinct from this app. This app is **"Timetables" (Teaching Rooms)**. Rebranded all user-facing text from "Room Bookings"/"LSTM Room Bookings" to "Timetables — Teaching Rooms" (top bar "Timetables · Teaching Rooms", login "Timetables — Teaching Room Bookings", tab titles "Timetables — …"). Verified via test client.
- Still to do (Daniel): add a **Timetables** tile on the trackon homepage → `/timetables/` (NOT labelled "Room Bookings").
