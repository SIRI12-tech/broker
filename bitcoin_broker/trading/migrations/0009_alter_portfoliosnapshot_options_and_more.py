# Generated by Django 5.1.3 on 2024-11-28 13:26

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0008_auto_20241128_1318'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='portfoliosnapshot',
            options={'get_latest_by': 'timestamp', 'ordering': ['-timestamp']},
        ),
        migrations.AlterUniqueTogether(
            name='portfoliosnapshot',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='economiccalendar',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='economiccalendar',
            name='event_date',
        ),
        migrations.RemoveField(
            model_name='economiccalendar',
            name='event_name',
        ),
        migrations.RemoveField(
            model_name='economiccalendar',
            name='importance',
        ),
        migrations.RemoveField(
            model_name='marketnews',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='marketnews',
            name='impact_level',
        ),
        migrations.RemoveField(
            model_name='marketnews',
            name='news_type',
        ),
        migrations.RemoveField(
            model_name='marketnews',
            name='published_at',
        ),
        migrations.RemoveField(
            model_name='marketnews',
            name='sentiment_score',
        ),
        migrations.RemoveField(
            model_name='marketsentiment',
            name='asset',
        ),
        migrations.RemoveField(
            model_name='marketsentiment',
            name='news_sentiment',
        ),
        migrations.RemoveField(
            model_name='marketsentiment',
            name='social_mentions',
        ),
        migrations.RemoveField(
            model_name='marketsentiment',
            name='updated_at',
        ),
        migrations.RemoveField(
            model_name='marketsentiment',
            name='volume_24h',
        ),
        migrations.AddField(
            model_name='economiccalendar',
            name='date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='economiccalendar',
            name='event',
            field=models.CharField(default='', max_length=200),
        ),
        migrations.AddField(
            model_name='economiccalendar',
            name='impact',
            field=models.CharField(choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], default='medium', max_length=20),
        ),
        migrations.AddField(
            model_name='marketnews',
            name='date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='marketnews',
            name='impact',
            field=models.CharField(choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], default='medium', max_length=20),
        ),
        migrations.AddField(
            model_name='marketsentiment',
            name='date',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='marketsentiment',
            name='description',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='marketsentiment',
            name='source',
            field=models.CharField(default='', max_length=100),
        ),
        migrations.AddField(
            model_name='portfoliosnapshot',
            name='asset_value',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name='portfoliosnapshot',
            name='pnl_24h',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name='portfoliosnapshot',
            name='pnl_percentage_24h',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='portfoliosnapshot',
            name='timestamp',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='economiccalendar',
            name='actual',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='economiccalendar',
            name='country',
            field=models.CharField(default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='economiccalendar',
            name='forecast',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='economiccalendar',
            name='previous',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='marketnews',
            name='content',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='marketnews',
            name='source',
            field=models.CharField(default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='marketnews',
            name='title',
            field=models.CharField(default='', max_length=200),
        ),
        migrations.AlterField(
            model_name='marketnews',
            name='url',
            field=models.URLField(default=''),
        ),
        migrations.AlterField(
            model_name='marketsentiment',
            name='sentiment_score',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=5),
        ),
        migrations.AlterField(
            model_name='portfoliosnapshot',
            name='cash_balance',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=20),
        ),
        migrations.AlterField(
            model_name='portfoliosnapshot',
            name='total_value',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=20),
        ),
        migrations.CreateModel(
            name='BacktestResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('initial_capital', models.DecimalField(decimal_places=8, max_digits=18)),
                ('final_capital', models.DecimalField(decimal_places=8, max_digits=18)),
                ('total_trades', models.IntegerField()),
                ('win_rate', models.DecimalField(decimal_places=2, max_digits=5)),
                ('profit_loss', models.DecimalField(decimal_places=8, max_digits=18)),
                ('max_drawdown', models.DecimalField(decimal_places=2, max_digits=5)),
                ('sharpe_ratio', models.DecimalField(decimal_places=2, max_digits=5)),
                ('strategy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trading.tradingstrategy')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.CharField(max_length=255, unique=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('suspended', 'Suspended')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='WalletTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('deposit', 'Deposit'), ('withdrawal', 'Withdrawal')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=8, max_digits=18)),
                ('currency', models.CharField(max_length=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('tx_hash', models.CharField(blank=True, max_length=255, null=True)),
                ('destination_address', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trading.wallet')),
            ],
        ),
        migrations.RemoveField(
            model_name='portfoliosnapshot',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='portfoliosnapshot',
            name='daily_profit_loss',
        ),
        migrations.RemoveField(
            model_name='portfoliosnapshot',
            name='daily_profit_loss_percentage',
        ),
        migrations.RemoveField(
            model_name='portfoliosnapshot',
            name='invested_value',
        ),
        migrations.RemoveField(
            model_name='portfoliosnapshot',
            name='snapshot_date',
        ),
    ]
