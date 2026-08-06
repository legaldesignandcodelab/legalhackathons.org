from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('DJANGO_SECRET_KEY', default='dev-secret-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'unfold',
    'unfold.contrib.filters',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'registrations',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASE_URL = config('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')

if DATABASE_URL.startswith('postgres'):
    import re
    m = re.match(r'postgres://(\w+):([^@]+)@([^:/]+):(\d+)/(\w+)', DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': m.group(5),
            'USER': m.group(1),
            'PASSWORD': m.group(2),
            'HOST': m.group(3),
            'PORT': m.group(4),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Europe/Zurich'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = config('MEDIA_ROOT', default=str(BASE_DIR / 'media'))

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS — allow GitHub Pages and local dev
CORS_ALLOWED_ORIGINS = [
    'https://www.legalhackathons.org',
    'https://legalhackathons.org',
    'http://localhost',
    'http://127.0.0.1',
]
CORS_ALLOW_METHODS = ['GET', 'POST', 'DELETE', 'OPTIONS']
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    'https://www.legalhackathons.org',
    'https://legalhackathons.org',
    'http://localhost',
    'http://127.0.0.1',
]
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'None'

# Email
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Legal Hackathon <legal-hackathon@unisg.ch>')

ANYMAIL = {
    'RESEND_API_KEY': config('RESEND_API_KEY', default=''),
}

SITE_BASE_URL = config('SITE_BASE_URL', default='http://localhost')

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.AnonRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'anon': '20/hour'},
}

UNFOLD = {
    'SITE_TITLE': 'Legal Hackathon',
    'SITE_HEADER': 'Legal Hackathon',
    'SITE_SYMBOL': 'gavel',
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': False,
    'COLORS': {
        'font': {
            'subtle-light': '107 114 128',
            'subtle-dark': '156 163 175',
            'default-light': '75 85 99',
            'default-dark': '209 213 219',
            'important-light': '17 24 39',
            'important-dark': '243 244 246',
        },
        'primary': {
            '50':  '240 249 255',
            '100': '224 242 254',
            '200': '186 230 253',
            '300': '125 211 252',
            '400': '56 189 248',
            '500': '14 165 233',
            '600': '2 132 199',
            '700': '3 105 161',
            '800': '7 89 133',
            '900': '12 74 110',
            '950': '8 47 73',
        },
    },
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': False,
        'navigation': [
            {
                'title': 'Overview',
                'items': [
                    {
                        'title': 'Check-in Dashboard',
                        'icon': 'how_to_reg',
                        'link': '/admin/registrations/registration/checkin-overview/',
                    },
                    {
                        'title': 'Submissions Overview',
                        'icon': 'folder_open',
                        'link': '/admin/registrations/registration/submissions-overview/',
                    },
                    {
                        'title': 'Assignment Preview',
                        'icon': 'preview',
                        'link': '/admin/registrations/registration/assignment-preview/',
                    },
                ],
            },
            {
                'title': 'Participants',
                'items': [
                    {
                        'title': 'Registrations',
                        'icon': 'person',
                        'link': '/admin/registrations/registration/',
                        'badge': 'registrations.admin.registration_pending_count',
                    },
                    {
                        'title': 'Teams',
                        'icon': 'groups',
                        'link': '/admin/registrations/team/',
                    },
                ],
            },
            {
                'title': 'Hackathon',
                'items': [
                    {
                        'title': 'Challenges',
                        'icon': 'emoji_events',
                        'link': '/admin/registrations/challenge/',
                    },
                    {
                        'title': 'Preferences',
                        'icon': 'ballot',
                        'link': '/admin/registrations/challengepreference/',
                    },
                    {
                        'title': 'Assignments',
                        'icon': 'assignment',
                        'link': '/admin/registrations/challengeassignment/',
                    },
                    {
                        'title': 'Submissions',
                        'icon': 'upload_file',
                        'link': '/admin/registrations/submission/',
                    },
                    {
                        'title': 'Announcements',
                        'icon': 'campaign',
                        'link': '/admin/registrations/announcement/',
                    },
                    {
                        'title': 'Schedule',
                        'icon': 'schedule',
                        'link': '/admin/registrations/scheduleitem/',
                    },
                ],
            },
            {
                'title': 'Configuration',
                'items': [
                    {
                        'title': 'Site Settings',
                        'icon': 'settings',
                        'link': '/admin/registrations/sitesettings/',
                    },
                    {
                        'title': 'Users',
                        'icon': 'manage_accounts',
                        'link': '/admin/auth/user/',
                    },
                ],
            },
        ],
    },
}
