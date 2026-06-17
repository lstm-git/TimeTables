# Deploying the POC to a Linux VM (SQLite, dev-login)

This is the proof-of-concept deployment: no database server, simple dev-login,
served by waitress and kept alive by systemd. Assumes a Debian/Ubuntu-style VM.

Adjust paths/users to taste. `<vm-host>` = the VM's hostname or IP.

---

## 1. Get the code onto the VM

```bash
sudo mkdir -p /opt/timetables
sudo chown $USER:$USER /opt/timetables
git clone https://github.com/lstm-git/TimeTables.git /opt/timetables
cd /opt/timetables
```
(Private repo — use a GitHub Personal Access Token as the password, or an SSH deploy key.)

## 2. Python environment + dependencies

```bash
sudo apt update && sudo apt install -y python3-venv
cd /opt/timetables
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
(`psycopg2-binary` installs but is unused with SQLite — harmless.)

## 3. Get the data across (the bit git doesn't carry)

The 1,238 imported bookings live in a single SQLite file that is **gitignored**,
so the clone has no data. Copy it from your machine to the VM:

```bash
# run on your local machine, from the project folder:
scp instance/timetables.db <user>@<vm-host>:/opt/timetables/instance/timetables.db
```
If `instance/` doesn't exist yet on the VM: `mkdir -p /opt/timetables/instance` first.
Keep this file on the VM's local disk (never on a synced/OneDrive path — it corrupts SQLite).

> Empty-DB fallback: if you skip this, the app still starts but the grid is blank.
> You'd then need to copy the `.xlsx` over and run `.venv/bin/python import_spreadsheet.py`.

## 4. Secret key

Generate one and keep it stable so logins survive restarts:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Put it in an env file (next step). Do NOT leave the default `dev-only-change-me`.

## 5. Run as a service (systemd)

Create `/etc/timetables.env` (owned by root, mode 600):
```
SECRET_KEY=<paste the generated key>
# DATABASE_URL intentionally unset -> uses SQLite instance/timetables.db
# AZURE_* intentionally unset -> dev-login form (POC)
```

Create `/etc/systemd/system/timetables.service`:
```ini
[Unit]
Description=LSTM Room Bookings (POC)
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/timetables
EnvironmentFile=/etc/timetables.env
ExecStart=/opt/timetables/.venv/bin/waitress-serve --listen=0.0.0.0:8000 wsgi:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```
Make sure the service user can read/write the DB:
```bash
sudo chown -R www-data:www-data /opt/timetables/instance
```
Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now timetables
sudo systemctl status timetables      # check it's running
```

## 6. Open the port

```bash
sudo ufw allow 8000/tcp      # if ufw is in use
```
App is now at: **http://<vm-host>:8000/**

(Optional, for a tidy URL on the trackon page: put nginx in front proxying
port 80 -> 127.0.0.1:8000, then bind waitress to 127.0.0.1 instead of 0.0.0.0.)

## 7. Link it on the trackon front page

Add a link to `http://<vm-host>:8000/` (or the nginx URL).

---

## Updating later

```bash
cd /opt/timetables
git pull
.venv/bin/pip install -r requirements.txt   # only if requirements changed
sudo systemctl restart timetables
```
The `instance/timetables.db` is untouched by `git pull`, so data persists.

## POC caveats (so nobody's surprised)

- **Dev-login = no real security**: anyone who can reach the URL types any name and is in. Fine on the internal network for a demo; swap to Entra SSO before real use.
- **SQLite**: fine for a demo and light use; not for many people booking at the same instant.
- **No HTTPS** in the direct-port setup; add nginx + a cert if it needs to look/behave production-like.
