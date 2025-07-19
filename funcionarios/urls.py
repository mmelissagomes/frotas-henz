from django.urls import path
from . import views

urlpatterns = [
    path('', views.pagina_funcionarios, name='pagina_funcionarios'),
]