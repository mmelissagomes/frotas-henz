import os
from pathlib import Path

# 🏗️ Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# 🔐 Segurança via variáveis de ambiente
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-chave-fallback')

DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# 📦 Apps instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # 🧩 Apps do projeto
    'blog',
    'veiculos',
    'funcionarios',
    'relatorios',
]

# ⚙️ Middlewares padrão
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# 🌐 URLs raiz
ROOT_URLCONF = 'site_melissa.urls'

# 🎨 Configuração de templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'blog' / 'templates'],
        'DIRS': [BASE_DIR / 'relatorios' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# 🚀 WSGI
WSGI_APPLICATION = 'site_melissa.wsgi.application'

# 🗄️ Banco de dados SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 🔐 Validação de senha
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 🌍 Localização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# 📁 Arquivos estáticos


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Aponte para onde estão, de fato, os arquivos estáticos:
STATICFILES_DIRS = [
    #os.path.join(BASE_DIR, 'assets'),              # seu assets global
    #os.path.join(BASE_DIR, 'blog', 'static'),      # varre blog/static/...
    #os.path.join(BASE_DIR, 'relatorios', 'static') # varre relatorios/static/...
]
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'


# 🔑 Redirecionamento de autenticação
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# 🆔 Chave primária padrão
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'