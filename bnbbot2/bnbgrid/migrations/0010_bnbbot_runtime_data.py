# Generated by Django 5.1.4 on 2025-02-02 15:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bnbgrid', '0009_alter_bnbbot_binance_api_key_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bnbbot',
            name='runtime_data',
            field=models.TextField(default='{}'),
        ),
    ]
