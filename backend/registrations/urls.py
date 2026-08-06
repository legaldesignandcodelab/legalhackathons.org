from django.urls import path
from django.middleware.csrf import get_token
from django.http import JsonResponse
from .views import (
    RegisterView, CheckInView, SiteStatusView, TeamBoardView,
    SetPasswordView, LoginView, LogoutView, MeView, MeUpdateView,
    TeamCreateView, TeamJoinView, TeamMineView,
    ChallengeListView, ChallengePreferenceView, ChallengeAssignmentView,
    ScheduleView, SubmissionView, AnnouncementListView,
    export_registrations_csv,
)


def csrf_view(request):
    return JsonResponse({'csrftoken': get_token(request)})


urlpatterns = [
    # CSRF
    path('csrf/', csrf_view, name='csrf'),

    # Public
    path('register/', RegisterView.as_view(), name='register'),
    path('checkin/<uuid:token>/', CheckInView.as_view(), name='checkin'),
    path('status/', SiteStatusView.as_view(), name='status'),
    path('teams/', TeamBoardView.as_view(), name='teams'),

    # Auth
    path('auth/set-password/', SetPasswordView.as_view(), name='set_password'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
    path('me/update/', MeUpdateView.as_view(), name='me_update'),

    # Teams (authenticated)
    path('teams/create/', TeamCreateView.as_view(), name='team_create'),
    path('teams/join/', TeamJoinView.as_view(), name='team_join'),
    path('teams/mine/', TeamMineView.as_view(), name='team_mine'),

    # Challenges
    path('challenges/', ChallengeListView.as_view(), name='challenge_list'),
    path('challenges/preference/', ChallengePreferenceView.as_view(), name='challenge_preference'),
    path('challenges/assignment/', ChallengeAssignmentView.as_view(), name='challenge_assignment'),

    # Announcements, Schedule & Submission
    path('announcements/', AnnouncementListView.as_view(), name='announcements'),
    path('schedule/', ScheduleView.as_view(), name='schedule'),
    path('submission/', SubmissionView.as_view(), name='submission'),

    # Staff
    path('export/registrations.csv', export_registrations_csv, name='export_csv'),
]
