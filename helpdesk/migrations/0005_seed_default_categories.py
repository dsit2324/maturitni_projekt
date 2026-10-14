from django.db import migrations


DEFAULT_CATEGORIES = [
    ("Hardware", "Počítače, notebooky a další zařízení."),
    ("Software", "Aplikace, programy a jejich chyby."),
    ("Síť a internet", "Připojení k síti, Wi-Fi a internetu."),
    ("Účty a přístupy", "Uživatelské účty, hesla a oprávnění."),
    ("Tiskárny a periferie", "Tiskárny, monitory a další periferie."),
    ("Ostatní", "Požadavky, které nespadají do jiné kategorie."),
]


def create_default_categories(apps, schema_editor):
    Category = apps.get_model("helpdesk", "Category")
    for name, description in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(
            name=name,
            defaults={"description": description},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("helpdesk", "0004_alter_user_options_and_more"),
    ]

    operations = [
        migrations.RunPython(
            create_default_categories,
            migrations.RunPython.noop,
        ),
    ]