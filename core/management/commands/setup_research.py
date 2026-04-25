"""
Seed the database with default categories and create data directories.

Usage:
    python manage.py setup_research
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path

from config import CATEGORIES


class Command(BaseCommand):
    help = "Seed research categories and create data folder structure."

    def handle(self, *args, **options):
        from core.models import Category

        created = 0
        for slug, info in CATEGORIES.items():
            _, was_created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": info["label"],
                    "description": info["description"],
                    "icon": info["icon"],
                    "color": info["color"],
                },
            )
            if was_created:
                created += 1
                self.stdout.write(f"  Created category: {info['icon']} {info['label']}")
            else:
                self.stdout.write(f"  Exists:  {info['icon']} {info['label']}")

        # Create data directories
        data_dir = Path(settings.RESEARCH_DATA_DIR)
        for slug in list(CATEGORIES.keys()) + ["reports"]:
            folder = data_dir / slug
            folder.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Setup complete. {created} new categories created. "
            f"Data folder: {data_dir}"
        ))
