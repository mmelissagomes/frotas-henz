from django.urls import path
from . import views

urlpatterns = [
    path('', views.pagina_relatorios, name='pagina_relatorios'),
]