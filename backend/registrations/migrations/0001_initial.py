import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Registration',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('full_name', models.CharField(max_length=200)),
                ('email', models.EmailField(unique=True)),
                ('university', models.CharField(choices=[('hsg', 'HSG – University of St. Gallen'), ('other_swiss', 'Other Swiss University'), ('international', 'International University'), ('professional', 'Professional (not studying)'), ('other', 'Other')], max_length=50)),
                ('study_program', models.CharField(max_length=200)),
                ('year_of_study', models.CharField(choices=[('bachelor_1', 'Bachelor Year 1'), ('bachelor_2', 'Bachelor Year 2'), ('bachelor_3', 'Bachelor Year 3'), ('master_1', 'Master Year 1'), ('master_2', 'Master Year 2'), ('phd', 'PhD'), ('professional', 'Professional'), ('other', 'Other')], max_length=20)),
                ('knowledge_areas', models.JSONField(default=list)),
                ('team_preference', models.CharField(choices=[('solo_open', 'Solo – open to team matching'), ('solo_find', 'Solo – will find own team'), ('team_partial', 'Part of a team (2–3 people, looking for more)'), ('team_full', 'Full team of 4')], max_length=20)),
                ('dietary_restrictions', models.JSONField(default=list)),
                ('photo_consent', models.BooleanField()),
                ('code_of_conduct', models.BooleanField(default=False)),
                ('how_did_you_hear', models.CharField(blank=True, choices=[('email', 'Email'), ('social', 'Social Media'), ('word_of_mouth', 'Word of Mouth'), ('professor', 'Professor / Lecturer'), ('other', 'Other')], max_length=20)),
                ('cv', models.FileField(blank=True, null=True, upload_to='cvs/')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('waitlist', 'Waitlist'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('qr_token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('checked_in', models.BooleanField(default=False)),
                ('checked_in_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Registration',
                'verbose_name_plural': 'Registrations',
                'ordering': ['-created_at'],
            },
        ),
    ]
