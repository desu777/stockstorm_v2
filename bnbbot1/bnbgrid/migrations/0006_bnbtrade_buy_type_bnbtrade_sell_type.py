# Generated by Django 5.1.4 on 2025-01-28 14:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bnbgrid', '0005_remove_bnbtrade_stop_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='bnbtrade',
            name='buy_type',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name='bnbtrade',
            name='sell_type',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
