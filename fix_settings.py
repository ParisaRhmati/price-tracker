"""Patches settings.py for Docker — corrected indentation version."""
import sys
from pathlib import Path

settings_path = Path(__file__).parent / "backend" / "core" / "settings.py"
if not settings_path.exists():
    print(f"ERROR: {settings_path} not found")
    sys.exit(1)

text = settings_path.read_text(encoding="utf-8")
changed = False

# ── Patch: SQLite DB_PATH (unindented else: block) ───────────────────
old_sqlite = '''else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }'''

new_sqlite = '''else:
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
        print("Added DB_PATH support to SQLite config")
        changed = True
    else:
        print("ERROR: Could not find the SQLite block.")
        print("Searching for DATABASES...")
        idx = text.find("DATABASES")
        if idx >= 0:
            print("Found DATABASES at char", idx)
            print("Context:", repr(text[idx:idx+200]))
        sys.exit(1)
else:
    print("DB_PATH already present, skipping.")

if changed:
    settings_path.write_text(text, encoding="utf-8")
    print("settings.py patched successfully.")
else:
    print("No changes needed.")
