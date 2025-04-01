# Generated by Django 5.1.4 on 2025-01-26 15:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bnbgrid', '0002_remove_bnbtrade_limit_price_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bnbtrade',
            name='profit',
        ),
        migrations.AddField(
            model_name='bnbtrade',
            name='limit_price',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name='bnbtrade',
            name='stop_price',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
    ]
