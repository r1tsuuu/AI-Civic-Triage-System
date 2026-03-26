from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('triage', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='correctionlog',
            old_name='created_at',
            new_name='corrected_at',
        ),
    ]
