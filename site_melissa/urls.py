from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static

from site_melissa import settings


urlpatterns = [
    path('admin/', admin.site.urls),

    # 🔐 Login e Logout
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True
    ), name='login'),

    path('logout/', auth_views.LogoutView.as_view(
        next_page='login'
    ), name='logout'),

    # 🏠 Home conectada à app "blog"
    path('', include('blog.urls')),

    # 🔗 Apps conectadas
    path('veiculos/', include('veiculos.urls')),
    path('funcionarios/', include('funcionarios.urls')),
    path('relatorios/', include('relatorios.urls')),
]

if settings.DEBUG:urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
