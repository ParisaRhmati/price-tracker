"""Automatically patches backend/core/settings.py for Docker.

Run this ONCE from the price-tracker folder:
    python patch_settings.py

What it does:
  1. Adds STATIC_ROOT so collectstatic works inside Docker.
  2. Makes the SQLite path configurable via DB_PATH env var so Docker
     can store the database in a persistent volume.

Safe to run multiple times - it checks before making any change.
"""
import re
import sys
from pathlib import Path

settings_path = Path(__file__).parent / "backend" / "core" / "settings.py"

if not settings_path.exists():
    print(f"ERROR: Could not find {settings_path}")
    print("Make sure you run this script from inside the price-tracker folder.")
    sys.exit(1)

text = settings_path.read_text(encoding="utf-8")
changed = False

# ── Patch 1: STATIC_ROOT ──────────────────────────────────────────────
if "STATIC_ROOT" not in text:
    text = text.replace(
        'STATIC_URL = "static/"',
        'STATIC_URL = "static/"\nSTATIC_ROOT = BASE_DIR / "staticfiles"',
    )
    print("✓ Added STATIC_ROOT")
    changed = True
else:
    print("  STATIC_ROOT already present, skipping.")

# ── Patch 2: SQLite DB_PATH env var ───────────────────────────────────
old_sqlite = '''\
    else:
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": BASE_DIR / "db.sqlite3",
            }
        }'''

new_sqlite = '''\
    else:
        # DB_PATH env var lets Docker point SQLite to a named volume.
        # Falls back to the project root for normal local dev.
        _db_path = os.getenv("DB_PATH", "")
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": Path(_db_path) if _db_path else BASE_DIR / "db.sqlite3",
            }
        }'''

if "DB_PATH" not in text:
    if old_sqlite in text:
        text = text.replace(old_sqlite, new_sqlite)
        print("✓ Added DB_PATH support to SQLite config")
        changed = True
    else:
        print("  WARNING: Could not find the SQLite block to patch.")
        print("  Your settings.py may have a different format.")
        print("  Open backend/core/settings.py and find the SQLite DATABASES block,")
        print("  then add:  _db_path = os.getenv('DB_PATH', '')")
        print("  and change NAME to:  Path(_db_path) if _db_path else BASE_DIR / 'db.sqlite3'")
else:
    print("  DB_PATH already present, skipping.")

if changed:
    settings_path.write_text(text, encoding="utf-8")
    print("\n✓ settings.py patched successfully.")
else:
    print("\n  settings.py already up to date. No changes made.")
