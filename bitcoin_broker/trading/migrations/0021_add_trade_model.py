from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trading', '0020_auto_20241207_1113'),
    ]

    operations = [
        migrations.CreateModel(
            name='Trade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trade_type', models.CharField(choices=[('market', 'Market Order'), ('limit', 'Limit Order'), ('stop_loss', 'Stop Loss')], max_length=20)),
                ('side', models.CharField(choices=[('buy', 'Buy'), ('sell', 'Sell')], max_length=4)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('open', 'Open'), ('closed', 'Closed'), ('cancelled', 'Cancelled'), ('failed', 'Failed')], default='pending', max_length=10)),
                ('entry_price', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('exit_price', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('target_price', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('stop_loss_price', models.DecimalField(blank=True, decimal_places=8, max_digits=20, null=True)),
                ('quantity', models.DecimalField(decimal_places=8, max_digits=20)),
                ('filled_quantity', models.DecimalField(decimal_places=8, default=0, max_digits=20)),
                ('remaining_quantity', models.DecimalField(decimal_places=8, default=0, max_digits=20)),
                ('profit_loss', models.DecimalField(decimal_places=8, default=0, max_digits=20)),
                ('profit_loss_percentage', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('leverage', models.DecimalField(decimal_places=2, default=1.0, max_digits=5)),
                ('notes', models.TextField(blank=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trading.asset')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['user', 'status'], name='trading_tra_user_id_e06c1c_idx'),
                    models.Index(fields=['asset', 'trade_type'], name='trading_tra_asset_i_f8c5d7_idx'),
                ],
            },
        ),
    ]
