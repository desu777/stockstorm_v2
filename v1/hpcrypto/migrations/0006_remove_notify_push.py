# Generated by Django 5.1.4 on 2025-03-05 12:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hpcrypto', '0005_alter_pricealert_notify_push'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='pricealert',
            name='notify_push',
        ),
    ]
