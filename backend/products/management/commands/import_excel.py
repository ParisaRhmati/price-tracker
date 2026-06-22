"""Import products and sources from an Excel file:
    python manage.py import_excel /path/to/links.xlsx
    python manage.py import_excel /path/to/links.xlsx --sync

--sync makes the database an EXACT MIRROR of the spreadsheet: products and
source URLs that are no longer in the Excel get deleted. Without it, the
importer only adds and updates (never removes) — the safe default.
"""
from __future__ import annotations
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from products.services.excel_importer import import_excel


class Command(BaseCommand):
    help = "Import products and source URLs from links.xlsx."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to the .xlsx file")
        parser.add_argument(
            "--sync",
            action="store_true",
            help="Delete products/sources not present in the Excel (exact mirror).",
        )

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser().resolve()
        if not path.exists():
            raise CommandError(f"File not found: {path}")
        sync = options.get("sync", False)
        report = import_excel(str(path), sync=sync)
        for warning in report.warnings:
            self.stdout.write(self.style.WARNING(warning))
        if sync:
            self.stdout.write(self.style.SUCCESS("Import complete (SYNC mode — database mirrors Excel):"))
        else:
            self.stdout.write(self.style.SUCCESS("Import complete (add/update only):"))
        for key, value in report.as_dict().items():
            self.stdout.write(f"  {key}: {value}")
