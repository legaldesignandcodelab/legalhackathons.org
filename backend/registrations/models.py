import uuid
import random
import string
from django.db import models
from django.contrib.auth.models import User


class SiteSettings(models.Model):
    max_spots = models.PositiveIntegerField(default=100, help_text='Maximum confirmed registrations allowed.')
    registration_open = models.BooleanField(default=True, help_text='Uncheck to close registrations entirely.')
    auto_confirm = models.BooleanField(default=False, help_text='Automatically confirm pending registrations when a spot opens up.')
    preference_deadline = models.DateTimeField(null=True, blank=True, help_text='Global deadline for case preference submissions (leave blank = no deadline)')
    submission_deadline = models.DateTimeField(null=True, blank=True, help_text='Deadline for project submissions (leave blank = no deadline)')

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return f'Site Settings (max {self.max_spots} spots)'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Registration(models.Model):
    UNIVERSITY_CHOICES = [
        ('hsg', 'HSG – University of St. Gallen'),
        ('other_swiss', 'Other Swiss University'),
        ('international', 'International University'),
        ('professional', 'Professional (not studying)'),
        ('other', 'Other'),
    ]

    YEAR_CHOICES = [
        ('bachelor_1', 'Bachelor Year 1'),
        ('bachelor_2', 'Bachelor Year 2'),
        ('bachelor_3', 'Bachelor Year 3'),
        ('master_1', 'Master Year 1'),
        ('master_2', 'Master Year 2'),
        ('phd', 'PhD'),
        ('professional', 'Professional'),
        ('other', 'Other'),
    ]

    TEAM_CHOICES = [
        ('solo_open', 'Solo – open to team matching'),
        ('solo_find', 'Solo – will find own team'),
        ('team_partial', 'Part of a team (2–3 people, looking for more)'),
        ('team_full', 'Full team of 4'),
    ]

    HOW_CHOICES = [
        ('email', 'Email'),
        ('social', 'Social Media'),
        ('word_of_mouth', 'Word of Mouth'),
        ('professor', 'Professor / Lecturer'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('waitlist', 'Waitlist'),
        ('rejected', 'Rejected'),
    ]

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Personal info
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    university = models.CharField(max_length=50, choices=UNIVERSITY_CHOICES)
    study_program = models.CharField(max_length=200)
    year_of_study = models.CharField(max_length=20, choices=YEAR_CHOICES)

    # Skills & interests (stored as JSON list of strings)
    knowledge_areas = models.JSONField(default=list)

    # Team
    team_preference = models.CharField(max_length=20, choices=TEAM_CHOICES)

    # Logistics
    dietary_restrictions = models.JSONField(default=list)
    photo_consent = models.BooleanField()
    code_of_conduct = models.BooleanField(default=False)
    how_did_you_hear = models.CharField(max_length=20, choices=HOW_CHOICES, blank=True)

    # Social
    discord_handle = models.CharField(max_length=100, blank=True, help_text='Optional Discord username for team matching')

    # CV upload
    cv = models.FileField(upload_to='cvs/', blank=True, null=True)

    # Admin fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)

    # Check-in
    qr_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Registration'
        verbose_name_plural = 'Registrations'

    def __str__(self):
        return f'{self.full_name} ({self.email})'

    @property
    def knowledge_areas_display(self):
        return ', '.join(self.knowledge_areas) if self.knowledge_areas else '—'

    @property
    def dietary_display(self):
        return ', '.join(self.dietary_restrictions) if self.dietary_restrictions else 'None'

    @property
    def is_hsg(self):
        return self.email.endswith('@student.unisg.ch') and self.university == 'hsg'


class ParticipantUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='participant')
    registration = models.OneToOneField(Registration, on_delete=models.CASCADE, related_name='participant_user')

    def __str__(self):
        return f'ParticipantUser({self.registration.email})'


def _generate_invite_code():
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        if not Team.objects.filter(invite_code=code).exists():
            return code


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    invite_code = models.CharField(max_length=6, unique=True, editable=False)
    created_by = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='created_teams')
    members = models.ManyToManyField(Registration, through='TeamMember', related_name='teams')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = _generate_invite_code()
        super().save(*args, **kwargs)

    @property
    def member_count(self):
        return self.teammember_set.count()

    @property
    def is_full(self):
        return self.member_count >= 4


class TeamMember(models.Model):
    ROLE_CHOICES = [('owner', 'Owner'), ('member', 'Member')]

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('team', 'registration')]

    def __str__(self):
        return f'{self.registration.full_name} in {self.team.name} ({self.role})'


class Announcement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    is_published = models.BooleanField(default=True, help_text='Uncheck to hide without deleting')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'

    def __str__(self):
        return self.title


class ScheduleItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(null=True, blank=True, help_text='Date of this schedule item (e.g. 2026-11-07)')
    time_label = models.CharField(max_length=50, help_text='e.g. "09:00" or "09:00–09:30"')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    day = models.PositiveIntegerField(default=1, help_text='Day number (1 = Day 1, 2 = Day 2, …)')
    order = models.PositiveIntegerField(default=0)
    is_highlight = models.BooleanField(default=False, help_text='Show in accent colour')

    class Meta:
        ordering = ['day', 'order', 'time_label']
        verbose_name = 'Schedule Item'
        verbose_name_plural = 'Schedule Items'

    def __str__(self):
        return f'Day {self.day} {self.time_label} — {self.title}'


class Challenge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    sponsor = models.CharField(max_length=200, blank=True)
    sponsor_description = models.TextField(blank=True, help_text='Short description of the sponsor company')
    short_description = models.TextField(blank=True, help_text='1–2 sentence teaser shown on the card')
    description = models.TextField(blank=True, help_text='Full challenge description')
    deep_dive = models.TextField(blank=True, help_text='Technical/detailed background — shown in detail view')
    judging_criteria = models.TextField(blank=True, help_text='How submissions will be judged (shown in detail view)')
    resources_text = models.TextField(blank=True, help_text='Links, notes — only shown to assigned teams after assignment is published')
    resource_file = models.FileField(upload_to='challenge_resources/', blank=True, null=True, help_text='File only shown to assigned teams after assignment is published')
    max_teams = models.PositiveIntegerField(default=3, help_text='Maximum number of teams that can work on this challenge')
    is_published = models.BooleanField(default=False, help_text='Make visible to participants')
    assignment_published = models.BooleanField(default=False, help_text='Show team assignments to participants')
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0, help_text='Display order (lower = first)')

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Challenge'
        verbose_name_plural = 'Challenges'

    def __str__(self):
        return self.title

    @property
    def assigned_team_count(self):
        return self.assignments.count()


class ChallengePreference(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name='challenge_preference')
    prio1 = models.ForeignKey(Challenge, on_delete=models.SET_NULL, null=True, related_name='pref_prio1')
    prio2 = models.ForeignKey(Challenge, on_delete=models.SET_NULL, null=True, blank=True, related_name='pref_prio2')
    prio3 = models.ForeignKey(Challenge, on_delete=models.SET_NULL, null=True, blank=True, related_name='pref_prio3')
    submitted_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.team.name} preferences'


class ChallengeAssignment(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name='challenge_assignment')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text='Optional notes from organizers to the team')

    def __str__(self):
        return f'{self.team.name} → {self.challenge.title}'


class Submission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name='submission')
    repo_url = models.URLField(blank=True, help_text='GitHub / GitLab repo link')
    demo_url = models.URLField(blank=True, help_text='Live demo or video link')
    pitch_deck = models.FileField(upload_to='submissions/pitch_decks/', blank=True, null=True)
    additional_file = models.FileField(upload_to='submissions/files/', blank=True, null=True)
    notes = models.TextField(blank=True, help_text='Any notes for the jury')
    submitted_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Submission'
        verbose_name_plural = 'Submissions'

    def __str__(self):
        return f'Submission by {self.team.name}'
