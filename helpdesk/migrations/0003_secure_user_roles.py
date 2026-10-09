from django.db import migrations


def normalize_user_roles(apps, schema_editor):
    User = apps.get_model('helpdesk', 'User')
    database = schema_editor.connection.alias
    User.objects.using(database).filter(is_staff=True).update(role='admin')
    User.objects.using(database).filter(is_staff=False).update(role='user')


class Migration(migrations.Migration):
    dependencies = [
        ('helpdesk', '0002_ticket_updated_by_tickethistory'),
    ]

    operations = [
        migrations.RunPython(normalize_user_roles, migrations.RunPython.noop),
    ]