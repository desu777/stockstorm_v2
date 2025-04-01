# Generated by Django 5.1.4 on 2025-03-22 16:13

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hpcrypto', '0008_position_exit_date'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PendingOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_type', models.CharField(choices=[('STOP_LIMIT_BUY', 'Stop Limit Buy'), ('STOP_LIMIT_SELL', 'Stop Limit Sell')], max_length=20)),
                ('symbol', models.CharField(help_text='Trading symbol (e.g. BTC)', max_length=20)),
                ('currency', models.CharField(default='USDT', help_text='Quote currency (e.g. USDT, USDC)', max_length=10)),
                ('limit_price', models.DecimalField(decimal_places=8, help_text='Limit price for the order', max_digits=18)),
                ('trigger_price', models.DecimalField(decimal_places=8, help_text='Trigger price to activate the order', max_digits=18)),
                ('amount', models.DecimalField(decimal_places=8, help_text='Amount in quote currency (for buy) or asset quantity (for sell)', max_digits=18)),
                ('binance_order_id', models.CharField(blank=True, help_text='Order ID on Binance', max_length=50, null=True)),
                ('binance_client_order_id', models.CharField(blank=True, help_text='Client order ID on Binance', max_length=50, null=True)),
                ('status', models.CharField(choices=[('WAITING', 'Waiting'), ('CREATED', 'Created on Binance'), ('EXECUTED', 'Executed'), ('CANCELLED', 'Cancelled'), ('ERROR', 'Error')], default='WAITING', max_length=20)),
                ('last_checked', models.DateTimeField(blank=True, help_text='Last time this order was checked', null=True)),
                ('error_message', models.TextField(blank=True, help_text='Error message if any', null=True)),
                ('retry_count', models.IntegerField(default=0, help_text='Number of retries for order creation/checking')),
                ('position_identifier', models.CharField(blank=True, help_text='Position identifier (e.g. HP1)', max_length=50, null=True)),
                ('notes', models.TextField(blank=True, help_text='Additional notes about this order', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('executed_at', models.DateTimeField(blank=True, help_text='When the order was executed', null=True)),
                ('category', models.ForeignKey(blank=True, help_text='Category for buy orders', null=True, on_delete=django.db.models.deletion.SET_NULL, to='hpcrypto.hpcategory')),
                ('position', models.ForeignKey(blank=True, help_text='Related position for sell orders', null=True, on_delete=django.db.models.deletion.SET_NULL, to='hpcrypto.position')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pending Order',
                'verbose_name_plural': 'Pending Orders',
                'ordering': ['-created_at'],
            },
        ),
    ]
