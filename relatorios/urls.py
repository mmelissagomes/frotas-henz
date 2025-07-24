from django.urls import path
from . import views


urlpatterns = [
    path("", views.pagina_relatorios, name="pagina_relatorios"),
    path("api/relatorios/mensal-completo/<str:mes>/<str:ano>/pdf/", views.gerar_relatorio_mensal_completo_pdf),
    path("api/relatorios/mensal/<str:placa>/<str:mes>/pdf/", views.gerar_relatorio_mensal_pdf),
    path("api/relatorios/debug/mensal/<str:placa>/<str:mes>/",views.debug_relatorio_html,name="debug_relatorio_html")


]
