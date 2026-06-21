"""Import products and sources from an Excel file:

    python manage.py import_excel /path/to/links.xlsx
"""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from products.services.excel_importer import import_excel


class Command(BaseCommand):
    help = "Import products and source URLs from links.xlsx."

    def add_arguments(self, parser):
        parser.add_argument("path", type=str, help="Path to the .xlsx file")

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser().resolve()
        if not path.exists():
            raise CommandError(f"File not found: {path}")

        report = import_excel(str(path))
        for warning in report.warnings:
            self.stdout.write(self.style.WARNING(warning))

        self.stdout.write(self.style.SUCCESS("Import complete:"))
        for key, value in report.as_dict().items():
            self.stdout.write(f"  {key}: {value}")
