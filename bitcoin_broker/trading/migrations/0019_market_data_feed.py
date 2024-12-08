from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0018_update_userprofile'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketDataFeed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset_name', models.CharField(max_length=100)),
                ('symbol', models.CharField(max_length=20)),
                ('price', models.DecimalField(decimal_places=8, max_digits=20)),
                ('bid', models.DecimalField(decimal_places=8, max_digits=20)),
                ('ask', models.DecimalField(decimal_places=8, max_digits=20)),
                ('volume_24h', models.DecimalField(decimal_places=8, max_digits=24)),
                ('high_24h', models.DecimalField(decimal_places=8, max_digits=20)),
                ('low_24h', models.DecimalField(decimal_places=8, max_digits=20)),
                ('data_source', models.CharField(choices=[('binance', 'Binance'), ('coinbase', 'Coinbase'), ('kraken', 'Kraken'), ('manual', 'Manual Entry'), ('other', 'Other')], max_length=20)),
                ('feed_status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('pending', 'Pending Approval'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Market Data Feed',
                'verbose_name_plural': 'Market Data Feeds',
                'ordering': ['-last_updated'],
            },
        ),
    ]
