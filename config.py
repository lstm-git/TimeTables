"""App configuration — everything sensitive comes from environment variables.

Local dev needs nothing set: it falls back to a SQLite file in instance/
and a simple name/email login form. On the VM, set:

    SECRET_KEY            random string for session signing
    DATABASE_URL          e.g. postgresql+psycopg2://user:pass@localhost/timetables
    AZURE_CLIENT_ID       Entra app registration (enables Microsoft sign-in)
    AZURE_CLIENT_SECRET
    AZURE_TENANT_ID
"""
import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///timetables.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Microsoft Entra ID (Azure Enterprise App). If AZURE_CLIENT_ID is unset
    # the app runs in dev-login mode (plain name/email form).
    AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")

    @property
    def AZURE_AUTHORITY(self):
        return f"https://login.microsoftonline.com/{self.AZURE_TENANT_ID}"
