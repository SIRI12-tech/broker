from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0024_rename_trade_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='trade',
            name='opened_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='trade',
            name='fee',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=20),
        ),
    ]
