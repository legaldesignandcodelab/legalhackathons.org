import csv
import logging
from django.http import HttpResponse, JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Registration, SiteSettings, ParticipantUser, Team, TeamMember, Challenge, ChallengePreference, ChallengeAssignment, ScheduleItem, Submission, Announcement
from .serializers import RegistrationSerializer
from .emails import (
    send_confirmation_email, send_waitlist_email,
    send_received_email, send_set_password_email,
)

logger = logging.getLogger(__name__)


# ── Helper ──────────────────────────────────────────────────────────────────

def _create_participant_user(registration):
    if ParticipantUser.objects.filter(registration=registration).exists():
        return
    user = User.objects.create_user(
        username=registration.email,
        email=registration.email,
        password=None,
        is_active=True,
    )
    ParticipantUser.objects.create(user=user, registration=registration)
    try:
        send_set_password_email(registration, user)
    except Exception as e:
        logger.error('Failed to send set-password email to %s: %s', registration.email, e)


def _participant_or_401(request):
    if not request.user.is_authenticated:
        return None, Response({'error': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
    try:
        pu = request.user.participant
        return pu.registration, None
    except ParticipantUser.DoesNotExist:
        return None, Response({'error': 'No participant profile found.'}, status=status.HTTP_403_FORBIDDEN)


# ── Public endpoints ─────────────────────────────────────────────────────────

class SiteStatusView(APIView):
    def get(self, request):
        settings = SiteSettings.get()
        confirmed = Registration.objects.filter(status='confirmed').count()
        spots_left = max(0, settings.max_spots - confirmed)
        return Response({
            'spots_left': spots_left,
            'max_spots': settings.max_spots,
            'confirmed': confirmed,
            'registration_open': settings.registration_open,
        })


class RegisterView(APIView):
    def post(self, request):
        site = SiteSettings.get()
        if not site.registration_open:
            return Response(
                {'errors': {'__all__': ['Registrations are currently closed.']}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        if Registration.objects.filter(email=serializer.validated_data['email']).exists():
            return Response(
                {'errors': {'email': ['This email is already registered.']}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        confirmed_count = Registration.objects.filter(status='confirmed').count()
        is_hsg = (
            serializer.validated_data['email'].endswith('@student.unisg.ch')
            and serializer.validated_data['university'] == 'hsg'
        )

        if is_hsg:
            reg_status = 'confirmed'
        elif confirmed_count >= site.max_spots:
            reg_status = 'waitlist'
        else:
            reg_status = 'pending'

        registration = serializer.save(status=reg_status)

        try:
            if reg_status == 'confirmed':
                send_confirmation_email(registration)
                _create_participant_user(registration)
            elif reg_status == 'waitlist':
                send_waitlist_email(registration)
            else:
                send_received_email(registration)
        except Exception as e:
            logger.error('Failed to send email to %s: %s', registration.email, e)

        if reg_status == 'confirmed':
            msg = 'You\'re in! Check your email for your confirmation and a link to set your portal password.'
        elif reg_status == 'waitlist':
            msg = 'You\'ve been added to the waitlist. We\'ll notify you if a spot opens up!'
        else:
            msg = 'Application received! We\'ll review it and get back to you within a few days.'

        return Response({'message': msg}, status=status.HTTP_201_CREATED)


class CheckInView(APIView):
    def get(self, request, token):
        try:
            reg = Registration.objects.get(qr_token=token)
        except Registration.DoesNotExist:
            return Response({'error': 'Invalid QR code.'}, status=status.HTTP_404_NOT_FOUND)

        if reg.status == 'rejected':
            return Response(
                {'error': f'Participant status is "{reg.get_status_display()}". Cannot check in.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        already_checked_in = reg.checked_in
        if not already_checked_in:
            reg.checked_in = True
            reg.checked_in_at = timezone.now()
            reg.save(update_fields=['checked_in', 'checked_in_at'])

        return Response({
            'already_checked_in': already_checked_in,
            'full_name': reg.full_name,
            'email': reg.email,
            'university': reg.get_university_display(),
            'team_preference': reg.get_team_preference_display(),
            'dietary_restrictions': reg.dietary_restrictions,
            'photo_consent': reg.photo_consent,
            'status': reg.get_status_display(),
            'checked_in_at': reg.checked_in_at,
        })


class TeamBoardView(APIView):
    def get(self, request):
        # Solo participants looking for a team
        solos = Registration.objects.filter(
            status='confirmed',
            team_preference='solo_open',
        ).order_by('created_at')

        solo_data = [{
            'type': 'solo',
            'id': str(r.id),
            'first_name': r.full_name.split()[0] if r.full_name else '',
            'study_program': r.study_program,
            'university': r.get_university_display(),
            'knowledge_areas': r.knowledge_areas,
            'discord_handle': r.discord_handle,
        } for r in solos if not TeamMember.objects.filter(registration=r).exists()]

        # Teams with open spots
        open_teams = []
        for team in Team.objects.all():
            members = list(TeamMember.objects.filter(team=team).select_related('registration'))
            if len(members) >= 4:
                continue
            all_skills = []
            for m in members:
                all_skills.extend(m.registration.knowledge_areas)
            open_teams.append({
                'type': 'team',
                'id': str(team.id),
                'team_name': team.name,
                'member_count': len(members),
                'spots_left': 4 - len(members),
                'knowledge_areas': list(dict.fromkeys(all_skills)),
                'members': [{
                    'first_name': m.registration.full_name.split()[0] if m.registration.full_name else '',
                    'study_program': m.registration.study_program,
                    'discord_handle': m.registration.discord_handle,
                } for m in members],
            })

        return Response({'solo': solo_data, 'teams': open_teams})


# ── Auth endpoints ────────────────────────────────────────────────────────────

class SetPasswordView(APIView):
    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        password = request.data.get('password', '')
        confirm = request.data.get('confirm_password', '')

        if not uid or not token:
            return Response({'error': 'Invalid link.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(password) < 8:
            return Response({'error': 'Password must be at least 8 characters.'}, status=status.HTTP_400_BAD_REQUEST)

        if password != confirm:
            return Response({'error': 'Passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (ValueError, User.DoesNotExist):
            return Response({'error': 'Invalid link.'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'This link has expired. Contact us for a new one.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save()
        login(request, user)
        return Response({'message': 'Password set successfully. You are now logged in.'})


class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({'error': 'Invalid email or password.'}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        try:
            reg = user.participant.registration
            return Response({
                'message': 'Logged in.',
                'full_name': reg.full_name,
                'status': reg.status,
            })
        except ParticipantUser.DoesNotExist:
            return Response({'error': 'No participant profile.'}, status=status.HTTP_403_FORBIDDEN)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Logged out.'})


class MeUpdateView(APIView):
    def post(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err
        discord = request.data.get('discord_handle', '').strip()
        reg.discord_handle = discord[:100]
        reg.save(update_fields=['discord_handle'])
        return Response({'message': 'Profile updated.'})


class MeView(APIView):
    def get(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err

        team_data = None
        tm = TeamMember.objects.filter(registration=reg).select_related('team').first()
        if tm:
            members = TeamMember.objects.filter(team=tm.team).select_related('registration')
            team_data = {
                'id': str(tm.team.id),
                'name': tm.team.name,
                'invite_code': tm.team.invite_code,
                'role': tm.role,
                'is_full': tm.team.is_full,
                'members': [{
                    'full_name': m.registration.full_name,
                    'study_program': m.registration.study_program,
                    'knowledge_areas': m.registration.knowledge_areas,
                    'role': m.role,
                } for m in members],
            }

        return Response({
            'id': str(reg.id),
            'full_name': reg.full_name,
            'email': reg.email,
            'university': reg.get_university_display(),
            'study_program': reg.study_program,
            'year_of_study': reg.get_year_of_study_display(),
            'knowledge_areas': reg.knowledge_areas,
            'discord_handle': reg.discord_handle,
            'team_preference': reg.get_team_preference_display(),
            'status': reg.status,
            'team': team_data,
        })


# ── Team endpoints ─────────────────────────────────────────────────────────────

class TeamCreateView(APIView):
    def post(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err

        if reg.status != 'confirmed':
            return Response({'error': 'Only confirmed participants can create teams.'}, status=status.HTTP_403_FORBIDDEN)

        if TeamMember.objects.filter(registration=reg).exists():
            return Response({'error': 'You are already in a team.'}, status=status.HTTP_400_BAD_REQUEST)

        name = request.data.get('name', '').strip()
        if not name:
            return Response({'error': 'Team name is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(name) > 100:
            return Response({'error': 'Team name must be under 100 characters.'}, status=status.HTTP_400_BAD_REQUEST)

        team = Team.objects.create(name=name, created_by=reg)
        TeamMember.objects.create(team=team, registration=reg, role='owner')

        return Response({
            'message': 'Team created!',
            'team_name': team.name,
            'invite_code': team.invite_code,
        }, status=status.HTTP_201_CREATED)


class TeamJoinView(APIView):
    def post(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err

        if reg.status != 'confirmed':
            return Response({'error': 'Only confirmed participants can join teams.'}, status=status.HTTP_403_FORBIDDEN)

        if TeamMember.objects.filter(registration=reg).exists():
            return Response({'error': 'You are already in a team.'}, status=status.HTTP_400_BAD_REQUEST)

        code = request.data.get('invite_code', '').strip().upper()
        try:
            team = Team.objects.get(invite_code=code)
        except Team.DoesNotExist:
            return Response({'error': 'Invalid invite code.'}, status=status.HTTP_404_NOT_FOUND)

        if team.is_full:
            return Response({'error': 'This team is already full (max 4 members).'}, status=status.HTTP_400_BAD_REQUEST)

        TeamMember.objects.create(team=team, registration=reg, role='member')
        return Response({'message': f'Joined team "{team.name}"!', 'team_name': team.name})


class TeamMineView(APIView):
    def get(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err

        tm = TeamMember.objects.filter(registration=reg).select_related('team').first()
        if not tm:
            return Response({'team': None})

        members = TeamMember.objects.filter(team=tm.team).select_related('registration')
        return Response({'team': {
            'id': str(tm.team.id),
            'name': tm.team.name,
            'invite_code': tm.team.invite_code,
            'role': tm.role,
            'is_full': tm.team.is_full,
            'member_count': tm.team.member_count,
            'members': [{
                'full_name': m.registration.full_name,
                'study_program': m.registration.study_program,
                'knowledge_areas': m.registration.knowledge_areas,
                'role': m.role,
            } for m in members],
        }})

    def delete(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err

        tm = TeamMember.objects.filter(registration=reg).select_related('team').first()
        if not tm:
            return Response({'error': 'You are not in a team.'}, status=status.HTTP_400_BAD_REQUEST)

        team = tm.team
        is_owner = tm.role == 'owner'
        tm.delete()

        if is_owner:
            remaining = TeamMember.objects.filter(team=team).order_by('joined_at').first()
            if remaining:
                remaining.role = 'owner'
                remaining.save()
            else:
                team.delete()

        return Response({'message': 'Left the team.'})


# ── Challenge endpoints ───────────────────────────────────────────────────────

class ChallengeListView(APIView):
    """Published challenges. Deadline comes from SiteSettings."""
    def get(self, request):
        challenges = Challenge.objects.filter(is_published=True)
        site = SiteSettings.get()
        now = timezone.now()
        deadline = site.preference_deadline
        deadline_passed = bool(deadline and now > deadline)
        data = [{
            'id': str(c.id),
            'title': c.title,
            'sponsor': c.sponsor,
            'sponsor_description': c.sponsor_description,
            'short_description': c.short_description,
            'description': c.description,
            'deep_dive': c.deep_dive,
            'judging_criteria': c.judging_criteria,
            'order': c.order,
            'preference_deadline': deadline,
            'deadline_passed': deadline_passed,
        } for c in challenges]
        return Response(data)


class ChallengePreferenceView(APIView):
    """Team owner submits Prio 1/2/3 preferences."""
    def get(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err
        tm = TeamMember.objects.filter(registration=reg, role='owner').select_related('team').first()
        if not tm:
            return Response({'preference': None, 'is_owner': False})
        try:
            pref = tm.team.challenge_preference
            return Response({
                'is_owner': True,
                'preference': {
                    'prio1': str(pref.prio1.id) if pref.prio1 else None,
                    'prio2': str(pref.prio2.id) if pref.prio2 else None,
                    'prio3': str(pref.prio3.id) if pref.prio3 else None,
                    'submitted_at': pref.submitted_at,
                }
            })
        except ChallengePreference.DoesNotExist:
            return Response({'is_owner': True, 'preference': None})

    def post(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err
        tm = TeamMember.objects.filter(registration=reg, role='owner').select_related('team').first()
        if not tm:
            return Response({'error': 'Only team owners can submit preferences.'}, status=status.HTTP_403_FORBIDDEN)

        def get_challenge(cid):
            if not cid:
                return None
            try:
                return Challenge.objects.get(id=cid, is_published=True)
            except (Challenge.DoesNotExist, ValueError):
                return None

        prio1 = get_challenge(request.data.get('prio1'))
        prio2 = get_challenge(request.data.get('prio2'))
        prio3 = get_challenge(request.data.get('prio3'))

        if not prio1:
            return Response({'error': 'Prio 1 is required.'}, status=status.HTTP_400_BAD_REQUEST)

        deadline = SiteSettings.get().preference_deadline
        if deadline and timezone.now() > deadline:
            return Response({'error': 'The preference submission deadline has passed.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure no duplicates
        chosen = [c for c in [prio1, prio2, prio3] if c]
        if len(chosen) != len({c.id for c in chosen}):
            return Response({'error': 'Each priority must be a different challenge.'}, status=status.HTTP_400_BAD_REQUEST)

        ChallengePreference.objects.update_or_create(
            team=tm.team,
            defaults={'prio1': prio1, 'prio2': prio2, 'prio3': prio3},
        )
        return Response({'message': 'Preferences saved.'})


class ChallengeAssignmentView(APIView):
    """Returns the team's assignment once published."""
    def get(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err
        tm = TeamMember.objects.filter(registration=reg).select_related('team').first()
        if not tm:
            return Response({'assignment': None})
        try:
            asgn = tm.team.challenge_assignment
            if not asgn.challenge.assignment_published:
                return Response({'assignment': None})
            c = asgn.challenge
            return Response({'assignment': {
                'challenge_id': str(c.id),
                'challenge_title': c.title,
                'challenge_sponsor': c.sponsor,
                'challenge_sponsor_description': c.sponsor_description,
                'challenge_short_description': c.short_description,
                'challenge_description': c.description,
                'challenge_deep_dive': c.deep_dive,
                'challenge_judging_criteria': c.judging_criteria,
                'resources_text': c.resources_text,
                'resource_file_url': request.build_absolute_uri(c.resource_file.url) if c.resource_file else None,
                'notes': asgn.notes,
            }})
        except ChallengeAssignment.DoesNotExist:
            return Response({'assignment': None})


# ── Schedule endpoint ─────────────────────────────────────────────────────────

class AnnouncementListView(APIView):
    def get(self, request):
        items = Announcement.objects.filter(is_published=True)
        return Response([{
            'id': str(a.id),
            'title': a.title,
            'body': a.body,
            'created_at': timezone.localtime(a.created_at).strftime('%d %b %Y, %H:%M'),
        } for a in items])


class ScheduleView(APIView):
    def get(self, request):
        items = ScheduleItem.objects.all()
        days = {}
        for item in items:
            days.setdefault(item.day, []).append({
                'id': str(item.id),
                'date': item.date.strftime('%A, %d %B %Y') if item.date else None,
                'date_iso': item.date.strftime('%Y-%m-%d') if item.date else None,
                'time_label': item.time_label,
                'title': item.title,
                'description': item.description,
                'location': item.location,
                'is_highlight': item.is_highlight,
                'order': item.order,
            })
        return Response([{'day': d, 'items': days[d]} for d in sorted(days)])


# ── Submission endpoint ───────────────────────────────────────────────────────

class SubmissionView(APIView):
    def get(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err
        site = SiteSettings.get()
        now = timezone.now()
        deadline = site.submission_deadline
        tm = TeamMember.objects.filter(registration=reg).select_related('team').first()
        meta = {
            'in_team': bool(tm),
            'deadline': deadline,
            'deadline_passed': bool(deadline and now > deadline),
        }
        if not tm:
            return Response({**meta, 'submission': None})
        try:
            sub = tm.team.submission
            return Response({**meta, 'submission': {
                'repo_url': sub.repo_url,
                'demo_url': sub.demo_url,
                'has_pitch_deck': bool(sub.pitch_deck),
                'has_additional_file': bool(sub.additional_file),
                'notes': sub.notes,
                'submitted_at': sub.submitted_at,
            }})
        except Submission.DoesNotExist:
            return Response({**meta, 'submission': None})

    def post(self, request):
        reg, err = _participant_or_401(request)
        if err:
            return err
        tm = TeamMember.objects.filter(registration=reg).select_related('team').first()
        if not tm:
            return Response({'error': 'You must be in a team to submit.'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        files = request.FILES

        pitch_deck = files.get('pitch_deck')
        additional_file = files.get('additional_file')

        if pitch_deck:
            if not pitch_deck.name.lower().endswith('.pdf'):
                return Response({'error': 'Pitch deck must be a PDF.'}, status=status.HTTP_400_BAD_REQUEST)
            if pitch_deck.size > 20 * 1024 * 1024:
                return Response({'error': 'Pitch deck must be under 20 MB.'}, status=status.HTTP_400_BAD_REQUEST)

        deadline = SiteSettings.get().submission_deadline
        if deadline and timezone.now() > deadline:
            return Response({'error': 'The submission deadline has passed.'}, status=status.HTTP_400_BAD_REQUEST)

        sub, _ = Submission.objects.get_or_create(team=tm.team)
        sub.repo_url = data.get('repo_url', sub.repo_url or '')
        sub.demo_url = data.get('demo_url', sub.demo_url or '')
        sub.notes = data.get('notes', sub.notes or '')
        if pitch_deck:
            sub.pitch_deck = pitch_deck
        if additional_file:
            sub.additional_file = additional_file
        sub.save()

        return Response({'message': 'Submission saved.'})


# ── Staff export ──────────────────────────────────────────────────────────────

@staff_member_required
def export_registrations_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="registrations_all.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Full Name', 'Email', 'University', 'Study Program', 'Year of Study',
        'Knowledge Areas', 'Team Preference', 'Dietary Restrictions',
        'Photo Consent', 'How Did You Hear', 'CV Uploaded', 'Status',
        'Team Name', 'Team Role', 'Checked In', 'Checked In At', 'Registered At',
    ])
    for r in Registration.objects.all():
        tm = TeamMember.objects.filter(registration=r).select_related('team').first()
        writer.writerow([
            str(r.id), r.full_name, r.email,
            r.get_university_display(), r.study_program, r.get_year_of_study_display(),
            r.knowledge_areas_display, r.get_team_preference_display(),
            r.dietary_display, 'Yes' if r.photo_consent else 'No',
            r.get_how_did_you_hear_display() if r.how_did_you_hear else '',
            'Yes' if r.cv else 'No',
            r.get_status_display(),
            tm.team.name if tm else '',
            tm.role if tm else '',
            'Yes' if r.checked_in else 'No',
            r.checked_in_at.strftime('%Y-%m-%d %H:%M') if r.checked_in_at else '',
            r.created_at.strftime('%Y-%m-%d %H:%M'),
        ])
    return response
