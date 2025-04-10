# Generated by Django 5.1.4 on 2025-03-03 15:16

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='HPCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('description', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'HP Categories',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Position',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticker', models.CharField(max_length=20)),
                ('quantity', models.DecimalField(decimal_places=8, max_digits=18)),
                ('entry_price', models.DecimalField(decimal_places=8, max_digits=18)),
                ('exit_price', models.DecimalField(blank=True, decimal_places=8, max_digits=18, null=True)),
                ('current_price', models.DecimalField(blank=True, decimal_places=8, max_digits=18, null=True)),
                ('last_price_update', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='positions', to='hpcrypto.hpcategory')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PriceAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('alert_type', models.CharField(choices=[('PRICE_ABOVE', 'Price Above'), ('PRICE_BELOW', 'Price Below'), ('PCT_INCREASE', '% Increase'), ('PCT_DECREASE', '% Decrease')], max_length=20)),
                ('threshold_value', models.DecimalField(decimal_places=8, max_digits=18)),
                ('is_active', models.BooleanField(default=True)),
                ('triggered', models.BooleanField(default=False)),
                ('last_triggered', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('position', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='hpcrypto.position')),
            ],
        ),
    ]
