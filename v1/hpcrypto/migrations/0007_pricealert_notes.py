# Generated by Django 5.1.4 on 2025-03-10 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hpcrypto', '0006_remove_notify_push'),
    ]

    operations = [
        migrations.AddField(
            model_name='pricealert',
            name='notes',
            field=models.TextField(blank=True, help_text='Additional notes for this alert', null=True),
        ),
    ]
