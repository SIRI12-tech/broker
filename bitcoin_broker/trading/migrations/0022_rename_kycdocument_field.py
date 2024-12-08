from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0021_add_trade_model'),
    ]

    operations = [
        migrations.RenameField(
            model_name='kycdocument',
            old_name='submitted_at',
            new_name='uploaded_at',
        ),
    ]
