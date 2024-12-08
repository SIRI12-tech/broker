from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0022_rename_kycdocument_field'),
    ]

    operations = [
        migrations.RenameField(
            model_name='trade',
            old_name='filled_quantity',
            new_name='fee',
        ),
    ]
