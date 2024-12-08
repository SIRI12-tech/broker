from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0023_rename_trade_field'),
    ]

    operations = [
        migrations.RenameField(
            model_name='trade',
            old_name='exit_price',
            new_name='stop_loss',
        ),
        migrations.RenameField(
            model_name='trade',
            old_name='target_price',
            new_name='take_profit',
        ),
        migrations.RenameField(
            model_name='trade',
            old_name='stop_loss_price',
            new_name='trailing_stop',
        ),
        migrations.RenameField(
            model_name='trade',
            old_name='updated_at',
            new_name='opened_at',
        ),
    ]
