from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trading', '0017_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='date_of_birth',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='address',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='verification_status',
            field=models.CharField(choices=[('unverified', 'Unverified'), ('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')], default='unverified', max_length=20),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='is_phone_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='is_email_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='kyc_status',
            field=models.CharField(choices=[('not_submitted', 'Not Submitted'), ('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')], default='not_submitted', max_length=20),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='phone_number',
            field=models.CharField(blank=True, max_length=15, null=True),
        ),
    ]
