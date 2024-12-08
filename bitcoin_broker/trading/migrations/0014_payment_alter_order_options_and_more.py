# Generated by Django 5.1.3 on 2024-12-03 11:11

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0013_auto_20241128_2040'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_method', models.CharField(choices=[('card', 'Credit/Debit Card'), ('paypal', 'PayPal'), ('crypto', 'Cryptocurrency'), ('bank', 'Bank Transfer')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=18)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('refunded', 'Refunded')], default='pending', max_length=20)),
                ('provider_reference', models.CharField(blank=True, max_length=255, null=True)),
                ('provider_status', models.CharField(blank=True, max_length=100, null=True)),
                ('provider_response', models.JSONField(blank=True, null=True)),
                ('crypto_address', models.CharField(blank=True, max_length=255, null=True)),
                ('crypto_amount', models.DecimalField(blank=True, decimal_places=8, max_digits=18, null=True)),
                ('crypto_currency', models.CharField(blank=True, max_length=10, null=True)),
                ('tx_hash', models.CharField(blank=True, max_length=255, null=True)),
                ('card_last4', models.CharField(blank=True, max_length=4, null=True)),
                ('card_brand', models.CharField(blank=True, max_length=20, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-created_at']},
        ),
        migrations.AlterUniqueTogether(
            name='asset',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='order',
            name='asset',
        ),
        migrations.RemoveField(
            model_name='order',
            name='expires_at',
        ),
        migrations.RemoveField(
            model_name='order',
            name='filled_quantity',
        ),
        migrations.RemoveField(
            model_name='order',
            name='price',
        ),
        migrations.RemoveField(
            model_name='order',
            name='quantity',
        ),
        migrations.RemoveField(
            model_name='order',
            name='side',
        ),
        migrations.RemoveField(
            model_name='order',
            name='stop_price',
        ),
        migrations.RemoveField(
            model_name='order',
            name='trailing_percent',
        ),
        migrations.AddField(
            model_name='order',
            name='amount',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=18),
        ),
        migrations.AddField(
            model_name='order',
            name='crypto_asset',
            field=models.CharField(default='BTC', max_length=10),
        ),
        migrations.AlterField(
            model_name='asset',
            name='asset_type',
            field=models.CharField(choices=[('crypto', 'Cryptocurrency'), ('forex', 'Forex'), ('stock', 'Stock')], max_length=10),
        ),
        migrations.AlterField(
            model_name='asset',
            name='symbol',
            field=models.CharField(max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_type',
            field=models.CharField(choices=[('buy', 'Buy'), ('sell', 'Sell')], max_length=4),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=10),
        ),
        migrations.AlterField(
            model_name='order',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddIndex(
            model_name='asset',
            index=models.Index(fields=['asset_type', '-price_change_percentage_24h'], name='trading_ass_asset_t_cf0a3b_idx'),
        ),
        migrations.AddField(
            model_name='payment',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='trading.order'),
        ),
        migrations.RemoveField(
            model_name='asset',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='forex_base_currency',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='forex_quote_currency',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='stock_exchange',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='updated_at',
        ),
    ]
