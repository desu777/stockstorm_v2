# Generated by Django 5.1.4 on 2025-03-05 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hpcrypto', '0003_pricealert_sms_sent'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricealert',
            name='notify_push',
            field=models.BooleanField(default=True, help_text='Send push notification when alert triggered'),
        ),
        migrations.AddField(
            model_name='pricealert',
            name='notify_telegram',
            field=models.BooleanField(default=True, help_text='Send Telegram notification when alert triggered'),
        ),
    ]
