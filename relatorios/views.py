import logging
import base64
import requests

from datetime import datetime
from calendar import monthrange

from django.http            import HttpResponse
from django.shortcuts       import render
from django.template.loader import render_to_string

from weasyprint import HTML

from .planilha import (
    conectar_planilha,
    gerar_matriz_mensal,
    gerar_matriz_mensal_completo,
    construir_resposta_indexada,
    relacionar_id_envio_por_dia,
)

# Configura logging em nível INFO
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)


def carregar_logo_base64():
    """
    Lê o logo local e retorna um Data-URI em Base64.
    """
    caminho = "blog/static/blog_images/logo_blog.png"
    with open(caminho, "rb") as f:
        img_bytes = f.read()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def _injetar_assinatura_b64(dados):
    caminho = dados.get("assinatura", "").strip()
    try:
        if caminho.startswith("http"):
            response = requests.get(caminho, timeout=5)
            if response.status_code == 200:
                img_bytes = response.content
            else:
                raise Exception(f"Erro HTTP: {response.status_code}")
        else:
            with open(caminho, "rb") as f:
                img_bytes = f.read()

        ext = "jpeg" if caminho.lower().endswith((".jpg", ".jpeg")) else "png"
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        dados["assinatura"] = f"data:image/{ext};base64,{b64}"
    except Exception as e:
        logging.warning(f"Erro ao carregar assinatura: {e}")
        dados["assinatura"] = ""



def pagina_relatorios(request):
    """
    Exibe a página com selects de mês e ano.
    """
    meses = [
        ("01", "Janeiro"), ("02", "Fevereiro"), ("03", "Março"),
        ("04", "Abril"), ("05", "Maio"),      ("06", "Junho"),
        ("07", "Julho"), ("08", "Agosto"),    ("09", "Setembro"),
        ("10", "Outubro"), ("11", "Novembro"),("12", "Dezembro"),
    ]
    ano_atual = datetime.now().year
    anos = [str(a) for a in range(2022, ano_atual + 1)]
    return render(request, "relatorios/index.html", {
        "months": meses,
        "years":  anos,
    })


def gerar_relatorio_mensal_pdf(request, placa, mes):
    # 1) Dados iniciais
    logo_base64 = carregar_logo_base64()
    dados       = gerar_matriz_mensal(placa.strip().upper(), mes)
    ano, mes_int = int(dados["ano"]), int(dados["mes"])
    total_dias   = monthrange(ano, mes_int)[1]
    dias         = list(range(1, total_dias + 1))
    todos_ids = relacionar_id_envio_por_dia(conectar_planilha())
    placa_normalizada = placa.strip().upper()
    ids_filtrados = [
    r for r in todos_ids
    if r["placa"] == placa_normalizada and r["dia"] in dias
]


    # 2) Constrói o dict coluna→{dia→sigla}
    resposta = construir_resposta_indexada(
        matriz_respostas=dados["matriz"],
        cabecalho=dados["cabecalho"],
        dias=dias
    )

    # 3) Injeta assinatura como data URI
    _injetar_assinatura_b64(dados)
    logging.info(f"Assinatura data-URI (início): {dados['assinatura'][:50]}")

    # 4) Prepara contexto
    contexto = {
        "dados":       dados,
        "resposta":    resposta,
        "dias":        dias,
        "logo_base64": logo_base64,
        "relacoes_id": ids_filtrados,
    }

    # 5) Debug HTML
    if request.GET.get("format") == "html":
        return HttpResponse(
            render_to_string("relatorios/relatorio_mensal.html", contexto),
            content_type="text/html"
        )

    # 6) Geração do PDF
    html_string = render_to_string("relatorios/relatorio_mensal.html", contexto)
    pdf_bytes    = HTML(string=html_string).write_pdf()
    response     = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename     = f"relatorio_{dados['placa']}_{mes}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def gerar_relatorio_mensal_completo_pdf(request, mes, ano):
    # 1) Dados iniciais
    logo_base64 = carregar_logo_base64()
    todos_raw, dias = gerar_matriz_mensal_completo(mes)
    relacoes_id = relacionar_id_envio_por_dia(conectar_planilha())

    # 2) Renderiza cada relatório
    placas_html = []
    for dados in todos_raw:
        resposta = construir_resposta_indexada(
            matriz_respostas=dados["matriz"],
            cabecalho=dados["cabecalho"],
            dias=dias
        )
        dados["resposta"] = resposta

        _injetar_assinatura_b64(dados)
        placa_atual = str(dados.get("placa", "")).strip().upper()
        ids_filtrados = [
        r for r in relacoes_id
        if r["dia"] in dias and r.get("placa") == placa_atual
        ]

        html_placa = render_to_string(
            "relatorios/relatorio_mensal_completo.html",
            {
                "dados":        dados,
                "dias":         dias,
                "logo_base64":  logo_base64,
                "relacoes_id":  ids_filtrados,
                "quebra_pagina": True,
                "resposta": dados["resposta"],
            }
        )
        placas_html.append(html_placa)

    # 3) Gera PDF único
    combined_html = "\n".join(placas_html)
    pdf_bytes     = HTML(string=combined_html).write_pdf()
    response      = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename      = f"relatorio_mensal_completo_{mes}_{ano}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def debug_relatorio_html(request, placa, mes):
    dados      = gerar_matriz_mensal(placa.upper(), mes)
    dias       = list(range(1, 32))
    relacoes_id = relacionar_id_envio_por_dia(conectar_planilha())

    resposta = construir_resposta_indexada(
        matriz_respostas=dados["matriz"],
        cabecalho=dados["cabecalho"],
        dias=dias
    )
    dados["resposta"] = resposta

    _injetar_assinatura_b64(dados)
    logging.info(f"Assinatura data-URI (início): {dados['assinatura'][:50]}")
    logo_base64 = carregar_logo_base64()

    html = render_to_string("relatorios/relatorio_debug.html", {
        "dados":       dados,
        "dias":        dias,
        "logo_base64": logo_base64,
        "relacoes_id": relacoes_id,
    })
    return HttpResponse(html, content_type="text/html")
