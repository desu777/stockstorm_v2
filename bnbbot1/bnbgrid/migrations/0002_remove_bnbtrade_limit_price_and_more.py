# Generated by Django 5.1.4 on 2025-01-26 15:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bnbgrid', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='bnbtrade',
            name='limit_price',
        ),
        migrations.RemoveField(
            model_name='bnbtrade',
            name='stop_price',
        ),
        migrations.AddField(
            model_name='bnbtrade',
            name='close_price',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name='bnbtrade',
            name='open_price',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=14, null=True),
        ),
        migrations.AddField(
            model_name='bnbtrade',
            name='profit',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True),
        ),
    ]
