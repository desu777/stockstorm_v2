# Generated by Django 5.1.4 on 2025-03-21 12:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bnbgrid', '0010_bnbbot_runtime_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='bnbbot',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='bnbbot',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
