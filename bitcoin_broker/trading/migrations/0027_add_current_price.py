from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0026_remove_trade_trading_tra_asset_i_f8c5d7_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='trade',
            name='current_price',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=20),
        ),
    ]
