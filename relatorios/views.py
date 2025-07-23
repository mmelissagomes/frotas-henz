import logging
import base64
import requests
from datetime import datetime
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from weasyprint import HTML
from .planilha import (
    conectar_planilha,
    gerar_matriz_mensal,
    gerar_matriz_mensal_completo,
    construir_resposta_indexada,
    relacionar_id_envio_por_dia,
)

# Configura logging (opcional, para debug)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)

def carregar_logo_base64():
    """
    Lê o arquivo de logo e retorna como Data-URI em Base64.
    """
    caminho_logo = "blog/static/blog_images/logo_blog.png"
    with open(caminho_logo, "rb") as img_file:
        data = img_file.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def pagina_relatorios(request):
    """
    Página inicial que mostra select de mês e ano.
    """
    meses = [
        ("01", "Janeiro"), ("02", "Fevereiro"), ("03", "Março"),
        ("04", "Abril"),   ("05", "Maio"),      ("06", "Junho"),
        ("07", "Julho"),   ("08", "Agosto"),    ("09", "Setembro"),
        ("10", "Outubro"), ("11", "Novembro"),  ("12", "Dezembro"),
    ]
    ano_atual = datetime.now().year
    anos = [str(a) for a in range(2022, ano_atual + 1)]
    return render(request, "relatorios/index.html", {
        "months": meses,
        "years":  anos,
    })


def _injetar_assinatura_b64(dados):
    """
    Baixa a URL de assinatura (dados['assinatura']) e cria dados['assinatura_b64'].
    Se falhar, assinatura_b64 fica string vazia.
    """
    assinatura_url = dados.get("assinatura", "") or ""
    dados["assinatura_b64"] = ""

    if assinatura_url.startswith("http"):
        try:
            resp = requests.get(assinatura_url, timeout=5)
            resp.raise_for_status()
            mime = resp.headers.get("Content-Type", "image/png")
            b64 = base64.b64encode(resp.content).decode("utf-8")
            dados["assinatura_b64"] = f"data:{mime};base64,{b64}"
        except Exception as e:
            logging.warning(f"Não foi possível converter assinatura: {e}")


def gerar_relatorio_mensal_pdf(request, placa, mes):
    """
    Gera PDF de checklist para uma única placa e mês.
    """
    # 1) Carrega logo
    logo_base64 = carregar_logo_base64()

    # 2) Gera dados da planilha
    dados = gerar_matriz_mensal(placa.strip().upper(), mes)
    _injetar_assinatura_b64(dados)
    dias = list(range(1, 32))
    relacoes_id = relacionar_id_envio_por_dia(conectar_planilha())

    # 3) Constrói respostas formatadas
    resposta = construir_resposta_indexada(
        matriz_respostas=dados["matriz"],
        cabecalho=dados["cabecalho"],
        dias=dias
    )
    dados["resposta"] = resposta

    # 4) Converte assinatura em Base64
    _injetar_assinatura_b64(dados)

    # 5) Renderiza HTML
    html_string = render_to_string("relatorios/relatorio_mensal.html", {
        "dados":       dados,
        "dias":        dias,
        "logo_base64": logo_base64,
        "resposta": resposta,   
        "relacoes_id": relacoes_id,
    })

    # Debug opcional: grava o HTML que será transformado em PDF
    with open("relatorio_debug.html", "w", encoding="utf-8") as f:
        f.write(html_string)

    # 6) Gera PDF
    pdf_file = HTML(string=html_string).write_pdf()

    # 7) Retorna resposta HTTP com PDF
    response = HttpResponse(pdf_file, content_type="application/pdf")
    filename = f"relatorio_{dados['placa']}_{mes}.pdf"
    response["Content-Disposition"] = f"inline; filename={filename}"
    return response


def gerar_relatorio_mensal_completo_pdf(request, mes, ano):
    """
    Gera PDF de checklist para todas as placas de um mês (relatório completo).
    """
    # 1) Carrega logo e dados de todas as placas
    logo_base64 = carregar_logo_base64()
    todos_raw, dias = gerar_matriz_mensal_completo(mes)
    relacoes_id = relacionar_id_envio_por_dia(conectar_planilha())

    # 2) Para cada placa, gera um fragmento HTML
    placas_html = []
    for dados in todos_raw:
        resposta = construir_resposta_indexada(
            matriz_respostas=dados["matriz"],
            cabecalho=dados["cabecalho"],
            dias=dias
        )
        dados["resposta"] = resposta

        _injetar_assinatura_b64(dados)

        html_placa = render_to_string(
            "relatorios/relatorio_mensal_completo.html", {
                "dados":        dados,
                "dias":         dias,
                "logo_base64":  logo_base64,
                "relacoes_id":  relacoes_id,
                "quebra_pagina": True,
            }
        )
        placas_html.append(html_placa)

    # 3) Concatena todos os HTMLs e gera PDF único
    html_string = "\n".join(placas_html)
    pdf_file = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type="application/pdf")
    filename = f"relatorio_mensal_completo_{mes}_{ano}.pdf"
    response["Content-Disposition"] = f"inline; filename={filename}"
    return response
