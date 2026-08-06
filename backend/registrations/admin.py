import csv
import io
import qrcode
import base64
from django.contrib import admin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from django.db.models import Count
from unfold.admin import ModelAdmin, TabularInline
from .models import Registration, SiteSettings, Team, TeamMember, Challenge, ChallengePreference, ChallengeAssignment, ScheduleItem, Submission, Announcement
from .views import _create_participant_user
from .emails import send_confirmation_email


def registration_pending_count(request):
    count = Registration.objects.filter(status='pending').count()
    return str(count) if count > 0 else ''


@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    fieldsets = (
        ('Capacity', {'fields': ('max_spots', 'registration_open')}),
        ('Automation', {'fields': ('auto_confirm',)}),
        ('Cases', {'fields': ('preference_deadline',), 'description': 'Global deadline for all teams to submit case preferences.'}),
        ('Submission', {'fields': ('submission_deadline',), 'description': 'Deadline for project submissions.'}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


def export_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="registrations.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Full Name', 'Email', 'University', 'Study Program', 'Year of Study',
        'Knowledge Areas', 'Team Preference', 'Dietary Restrictions',
        'Photo Consent', 'How Did You Hear', 'CV Uploaded', 'Status',
        'Checked In', 'Checked In At', 'Registered At',
    ])
    for r in queryset:
        writer.writerow([
            str(r.id), r.full_name, r.email,
            r.get_university_display(), r.study_program, r.get_year_of_study_display(),
            r.knowledge_areas_display, r.get_team_preference_display(),
            r.dietary_display, 'Yes' if r.photo_consent else 'No',
            r.get_how_did_you_hear_display(), 'Yes' if r.cv else 'No',
            r.get_status_display(), 'Yes' if r.checked_in else 'No',
            r.checked_in_at.strftime('%Y-%m-%d %H:%M') if r.checked_in_at else '',
            r.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response

export_csv.short_description = 'Export selected as CSV'


def mark_confirmed(modeladmin, request, queryset):
    for reg in queryset.filter(status__in=('pending', 'waitlist')):
        reg.status = 'confirmed'
        reg.save()
        try:
            send_confirmation_email(reg)
            _create_participant_user(reg)
        except Exception:
            pass
    queryset.filter(status='confirmed').update(status='confirmed')

mark_confirmed.short_description = 'Confirm selected (send portal invite)'


def mark_waitlist(modeladmin, request, queryset):
    queryset.update(status='waitlist')

mark_waitlist.short_description = 'Move selected to Waitlist'


def mark_rejected(modeladmin, request, queryset):
    queryset.update(status='rejected')

mark_rejected.short_description = 'Mark selected as Rejected'


def mark_checked_in(modeladmin, request, queryset):
    queryset.filter(checked_in=False).update(checked_in=True, checked_in_at=timezone.now())

mark_checked_in.short_description = 'Mark selected as Checked In'


@admin.register(Registration)
class RegistrationAdmin(ModelAdmin):
    list_display = [
        'full_name', 'email', 'university', 'study_program',
        'team_preference', 'status', 'checked_in', 'created_at',
    ]
    list_filter = ['status', 'team_preference', 'university', 'checked_in', 'photo_consent']
    search_fields = ['full_name', 'email', 'study_program']
    readonly_fields = ['id', 'qr_token', 'qr_code_preview', 'created_at', 'updated_at', 'checked_in_at']
    actions = [export_csv, mark_confirmed, mark_waitlist, mark_rejected, mark_checked_in]

    fieldsets = (
        ('Personal Info', {
            'fields': ('id', 'full_name', 'email', 'university', 'study_program', 'year_of_study'),
        }),
        ('Skills & Team', {
            'fields': ('knowledge_areas', 'team_preference'),
        }),
        ('Logistics', {
            'fields': ('dietary_restrictions', 'photo_consent', 'how_did_you_hear'),
        }),
        ('Documents', {
            'fields': ('cv', 'code_of_conduct'),
        }),
        ('Admin', {
            'fields': ('status', 'notes'),
        }),
        ('Check-in', {
            'fields': ('qr_token', 'qr_code_preview', 'checked_in', 'checked_in_at'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def qr_code_preview(self, obj):
        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(str(obj.qr_token))
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        b64 = base64.b64encode(buf.getvalue()).decode()
        return format_html('<img src="data:image/png;base64,{}" style="width:120px;height:120px;">', b64)

    qr_code_preview.short_description = 'QR Code'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('team-matching/', self.admin_site.admin_view(self.team_matching_view), name='team_matching'),
            path('checkin-overview/', self.admin_site.admin_view(self.checkin_overview_view), name='checkin_overview'),
            path('submissions-overview/', self.admin_site.admin_view(self.submissions_overview_view), name='submissions_overview'),
            path('assignment-preview/', self.admin_site.admin_view(self.assignment_preview_view), name='assignment_preview'),
        ]
        return custom + urls

    def team_matching_view(self, request):
        solo_open = Registration.objects.filter(team_preference='solo_open', status='confirmed')
        teams = []
        assigned = set()
        participants = list(solo_open)
        for p in participants:
            if p.id in assigned:
                continue
            team = [p]
            assigned.add(p.id)
            p_areas = set(p.knowledge_areas)
            for q in participants:
                if q.id in assigned or len(team) >= 4:
                    continue
                q_areas = set(q.knowledge_areas)
                if p_areas & q_areas:
                    team.append(q)
                    assigned.add(q.id)
            if len(team) > 1:
                teams.append(team)

        context = {
            **self.admin_site.each_context(request),
            'title': 'Team Matching',
            'teams': teams,
            'unmatched': [p for p in participants if p.id not in {m.id for t in teams for m in t}],
        }
        return render(request, 'admin/team_matching.html', context)

    def checkin_overview_view(self, request):
        confirmed = Registration.objects.filter(status='confirmed').order_by('full_name')
        total = confirmed.count()
        checked_in = confirmed.filter(checked_in=True)
        not_checked_in = confirmed.filter(checked_in=False)
        checked_in_count = checked_in.count()

        context = {
            **self.admin_site.each_context(request),
            'title': 'Check-in Overview',
            'total': total,
            'checked_in_count': checked_in_count,
            'not_checked_in_count': total - checked_in_count,
            'percent': round(checked_in_count / total * 100) if total else 0,
            'checked_in': checked_in,
            'not_checked_in': not_checked_in,
        }
        return render(request, 'admin/checkin_overview.html', context)

    def submissions_overview_view(self, request):
        submissions = (
            Submission.objects
            .select_related('team', 'team__challenge_assignment__challenge')
            .order_by('team__name')
        )
        teams_without_submission = (
            Team.objects
            .exclude(id__in=submissions.values_list('team_id', flat=True))
            .select_related('challenge_assignment__challenge')
            .order_by('name')
        )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Submissions Overview',
            'submissions': submissions,
            'teams_without_submission': teams_without_submission,
            'submission_count': submissions.count(),
            'total_teams': Team.objects.count(),
        }
        return render(request, 'admin/submissions_overview.html', context)


    def assignment_preview_view(self, request):
        challenges = list(Challenge.objects.filter(is_published=True))
        if not challenges:
            context = {
                **self.admin_site.each_context(request),
                'title': 'Assignment Preview',
                'no_challenges': True,
            }
            return render(request, 'admin/assignment_preview.html', context)

        result = run_assignment_algorithm(challenges)

        # Group by challenge
        from collections import defaultdict
        by_challenge = defaultdict(list)
        unassigned_teams = []
        all_teams = {str(t.id): t for t in Team.objects.all()}
        challenge_map = {str(c.id): c for c in challenges}

        for team_id, challenge in result.items():
            team = all_teams.get(team_id)
            if team:
                pref = ChallengePreference.objects.filter(team=team).first()
                prio_achieved = None
                if pref:
                    if pref.prio1 and str(pref.prio1.id) == str(challenge.id):
                        prio_achieved = 1
                    elif pref.prio2 and str(pref.prio2.id) == str(challenge.id):
                        prio_achieved = 2
                    elif pref.prio3 and str(pref.prio3.id) == str(challenge.id):
                        prio_achieved = 3
                    else:
                        prio_achieved = None  # fallback
                by_challenge[str(challenge.id)].append({
                    'team': team,
                    'prio_achieved': prio_achieved,
                    'had_preference': pref is not None,
                })

        assigned_team_ids = set(result.keys())
        for team_id, team in all_teams.items():
            if team_id not in assigned_team_ids:
                unassigned_teams.append(team)

        # Stats
        total_teams = len(all_teams)
        assigned_count = len(result)
        prio1_count = sum(1 for entries in by_challenge.values() for e in entries if e['prio_achieved'] == 1)
        prio2_count = sum(1 for entries in by_challenge.values() for e in entries if e['prio_achieved'] == 2)
        prio3_count = sum(1 for entries in by_challenge.values() for e in entries if e['prio_achieved'] == 3)
        fallback_count = sum(1 for entries in by_challenge.values() for e in entries if e['prio_achieved'] is None)
        no_pref_count = sum(1 for entries in by_challenge.values() for e in entries if not e['had_preference'])

        challenge_rows = []
        for c in sorted(challenges, key=lambda x: x.order):
            entries = by_challenge.get(str(c.id), [])
            challenge_rows.append({
                'challenge': c,
                'entries': entries,
                'count': len(entries),
                'max_teams': c.max_teams,
            })

        context = {
            **self.admin_site.each_context(request),
            'title': 'Assignment Preview (Dry Run)',
            'no_challenges': False,
            'challenge_rows': challenge_rows,
            'unassigned_teams': unassigned_teams,
            'total_teams': total_teams,
            'assigned_count': assigned_count,
            'prio1_count': prio1_count,
            'prio2_count': prio2_count,
            'prio3_count': prio3_count,
            'fallback_count': fallback_count,
            'no_pref_count': no_pref_count,
            'run_url': '/admin/registrations/challenge/',
        }
        return render(request, 'admin/assignment_preview.html', context)


class TeamMemberInline(TabularInline):
    model = TeamMember
    extra = 1
    fields = ['registration', 'role', 'joined_at']
    readonly_fields = ['joined_at']
    can_delete = True
    autocomplete_fields = ['registration']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('registration')


@admin.register(Team)
class TeamAdmin(ModelAdmin):
    list_display = ['name', 'invite_code', 'member_count', 'created_by', 'created_at']
    search_fields = ['name', 'invite_code', 'created_by__full_name']
    readonly_fields = ['id', 'invite_code', 'created_at']
    autocomplete_fields = ['created_by']
    inlines = [TeamMemberInline]

    def member_count(self, obj):
        return obj.member_count
    member_count.short_description = 'Members'


# ── Challenge assignment algorithm ───────────────────────────────────────────

def run_assignment_algorithm(challenges):
    """
    Assigns teams to challenges based on submitted preferences.
    Strategy:
      1. Try to honour Prio 1 for all teams (shuffle to avoid bias).
      2. For teams that couldn't get Prio 1, try Prio 2, then Prio 3.
      3. Remaining teams (no prefs or all full) get the challenge with fewest assigned teams.
    Respects max_teams per challenge.
    """
    import random

    capacity = {str(c.id): c.max_teams for c in challenges}
    assigned = {}  # team_id -> challenge

    prefs = list(ChallengePreference.objects.select_related('team', 'prio1', 'prio2', 'prio3').all())
    random.shuffle(prefs)

    def try_assign(team, challenge):
        if challenge is None:
            return False
        cid = str(challenge.id)
        if cid not in capacity or capacity[cid] <= 0:
            return False
        assigned[str(team.id)] = challenge
        capacity[cid] -= 1
        return True

    for prio_attr in ('prio1', 'prio2', 'prio3'):
        remaining = [p for p in prefs if str(p.team.id) not in assigned]
        for pref in remaining:
            try_assign(pref.team, getattr(pref, prio_attr))

    all_teams = list(Team.objects.all())
    unassigned = [t for t in all_teams if str(t.id) not in assigned]
    published_challenges = [c for c in challenges if c.is_published]
    for team in unassigned:
        if not published_challenges:
            break
        best = max(published_challenges, key=lambda c: capacity.get(str(c.id), 0))
        if capacity.get(str(best.id), 0) > 0:
            try_assign(team, best)

    return assigned  # {team_id_str: Challenge}


def action_run_assignment(modeladmin, request, queryset):
    challenges = list(Challenge.objects.filter(is_published=True))
    if not challenges:
        modeladmin.message_user(request, 'No published challenges to assign.', level='warning')
        return

    ChallengeAssignment.objects.all().delete()

    result = run_assignment_algorithm(challenges)

    created = 0
    for team_id, challenge in result.items():
        try:
            team = Team.objects.get(id=team_id)
            ChallengeAssignment.objects.create(team=team, challenge=challenge)
            created += 1
        except Team.DoesNotExist:
            pass

    total_teams = Team.objects.count()
    modeladmin.message_user(
        request,
        f'Assignment complete: {created}/{total_teams} teams assigned. '
        f'Publish assignments when ready via "Publish assignments" action.'
    )

action_run_assignment.short_description = '🎯 Run assignment algorithm (clears existing)'


def action_publish_assignments(modeladmin, request, queryset):
    queryset.update(assignment_published=True)
    modeladmin.message_user(request, f'Assignments published for {queryset.count()} challenge(s).')

action_publish_assignments.short_description = '✅ Publish assignments to participants'


def action_unpublish_assignments(modeladmin, request, queryset):
    queryset.update(assignment_published=False)

action_unpublish_assignments.short_description = '🔒 Unpublish assignments'


def action_publish_challenges(modeladmin, request, queryset):
    queryset.update(is_published=True)

action_publish_challenges.short_description = '👁 Publish challenges (make visible)'


def action_unpublish_challenges(modeladmin, request, queryset):
    queryset.update(is_published=False)

action_unpublish_challenges.short_description = '🙈 Unpublish challenges'


class ChallengeAssignmentInline(TabularInline):
    model = ChallengeAssignment
    extra = 0
    readonly_fields = ['team', 'assigned_at']
    fields = ['team', 'notes', 'assigned_at']


@admin.register(Challenge)
class ChallengeAdmin(ModelAdmin):
    list_display = ['title', 'sponsor', 'max_teams', 'assigned_team_count', 'is_published', 'assignment_published', 'order']
    list_editable = ['max_teams', 'is_published', 'order']
    list_filter = ['is_published', 'assignment_published']
    search_fields = ['title', 'sponsor']
    readonly_fields = ['id', 'created_at', 'assigned_team_count']
    inlines = [ChallengeAssignmentInline]
    actions = [
        action_run_assignment,
        action_publish_challenges,
        action_unpublish_challenges,
        action_publish_assignments,
        action_unpublish_assignments,
    ]

    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'title', 'sponsor', 'sponsor_description', 'order', 'is_published'),
        }),
        ('Content (visible to all participants)', {
            'fields': ('short_description', 'description', 'deep_dive', 'judging_criteria'),
        }),
        ('Resources (only shown to assigned teams)', {
            'fields': ('resources_text', 'resource_file'),
        }),
        ('Assignment', {
            'fields': ('max_teams', 'assigned_team_count', 'assignment_published'),
        }),
        ('Meta', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def assigned_team_count(self, obj):
        return obj.assigned_team_count
    assigned_team_count.short_description = 'Assigned Teams'


@admin.register(ChallengePreference)
class ChallengePreferenceAdmin(ModelAdmin):
    list_display = ['team', 'prio1', 'prio2', 'prio3', 'submitted_at']
    readonly_fields = ['submitted_at']


@admin.register(ChallengeAssignment)
class ChallengeAssignmentAdmin(ModelAdmin):
    list_display = ['team', 'challenge', 'assigned_at']
    list_filter = ['challenge']
    search_fields = ['team__name', 'challenge__title']
    readonly_fields = ['assigned_at']
    fields = ['team', 'challenge', 'notes', 'assigned_at']


@admin.register(Announcement)
class AnnouncementAdmin(ModelAdmin):
    list_display = ['title', 'is_published', 'created_at']
    list_editable = ['is_published']
    search_fields = ['title', 'body']
    fieldsets = (
        (None, {'fields': ('title', 'body', 'is_published')}),
    )


@admin.register(ScheduleItem)
class ScheduleItemAdmin(ModelAdmin):
    list_display = ['day', 'date', 'time_label', 'title', 'location', 'is_highlight', 'order']
    list_editable = ['order', 'is_highlight']
    list_filter = ['day', 'date', 'is_highlight']
    search_fields = ['title', 'location']
    fieldsets = (
        (None, {'fields': ('day', 'date', 'order', 'time_label', 'title', 'description', 'location', 'is_highlight')}),
    )


@admin.register(Submission)
class SubmissionAdmin(ModelAdmin):
    list_display = ['team', 'challenge_name', 'has_pitch_deck', 'has_repo', 'submitted_at']
    list_filter = ['team__challenge_assignment__challenge']
    search_fields = ['team__name']
    readonly_fields = ['submitted_at', 'created_at']
    fieldsets = (
        ('Team', {'fields': ('team',)}),
        ('Submission', {'fields': ('repo_url', 'demo_url', 'pitch_deck', 'additional_file', 'notes')}),
        ('Meta', {'fields': ('submitted_at', 'created_at'), 'classes': ('collapse',)}),
    )

    def challenge_name(self, obj):
        try:
            return obj.team.challenge_assignment.challenge.title
        except Exception:
            return '—'
    challenge_name.short_description = 'Challenge'

    def has_pitch_deck(self, obj):
        return bool(obj.pitch_deck)
    has_pitch_deck.boolean = True
    has_pitch_deck.short_description = 'Pitch Deck'

    def has_repo(self, obj):
        return bool(obj.repo_url)
    has_repo.boolean = True
    has_repo.short_description = 'Repo'
