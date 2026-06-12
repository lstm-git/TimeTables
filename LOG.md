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
