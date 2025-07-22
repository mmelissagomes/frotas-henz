
from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),      # / → login.html
    path("home/", views.home_view, name="home"),   # /home/ → home.html
]
