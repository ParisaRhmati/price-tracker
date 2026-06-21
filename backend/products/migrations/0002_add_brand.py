"""Add Brand model, link products to it, and seed the first two brands.

Samsung is seeded as id=1 and Xiaomi as id=2, exactly as requested. The
importer auto-creates any further brands with the next available id.
"""
import django.db.models.deletion
from django.db import migrations, models


def seed_brands(apps, schema_editor):
    Brand = apps.get_model("products", "Brand")
    for pk, name in [(1, "SAMSUNG"), (2, "XIAOMI")]:
        if not Brand.objects.filter(pk=pk).exists():
            Brand.objects.create(pk=pk, name=name)


def unseed_brands(apps, schema_editor):
    Brand = apps.get_model("products", "Brand")
    Brand.objects.filter(name__in=["SAMSUNG", "XIAOMI"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Brand",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(db_index=True, max_length=120, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["id"],
            },
        ),
        migrations.AddField(
            model_name="product",
            name="brand",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="products",
                to="products.brand",
            ),
        ),
        migrations.RunPython(seed_brands, unseed_brands),
    ]
