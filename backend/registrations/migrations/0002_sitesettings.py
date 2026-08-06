from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registrations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('max_spots', models.PositiveIntegerField(default=100, help_text='Maximum confirmed registrations allowed.')),
                ('registration_open', models.BooleanField(default=True, help_text='Uncheck to close registrations entirely.')),
                ('auto_confirm', models.BooleanField(default=False, help_text='Automatically confirm pending registrations when a spot opens up.')),
            ],
            options={
                'verbose_name': 'Site Settings',
                'verbose_name_plural': 'Site Settings',
            },
        ),
    ]
