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


def _injetar_assinatura_b64(dados):
    """
    Se dados['assinatura'] for URL de imagem, baixa e gera dados['assinatura_b64'].
    Em falha, assinatura_b64 fica string vazia.
    """
    assinatura_url = dados.get("assinatura", "") or ""
    dados["assinatura_b64"] = ""

    if assinatura_url.startswith("http"):
        try:
            resp = requests.get(assinatura_url, timeout=10)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "image/png")
            b64 = base64.b64encode(resp.content).decode("utf-8")
            dados["assinatura_b64"] = f"data:{content_type};base64,{b64}"
        except Exception as e:
            logging.warning(f"Não foi possível converter assinatura em base64: {e}")


def gerar_relatorio_mensal_pdf(request, placa, mes):
    """
    Gera PDF de checklist para uma única placa no mês especificado.

    Se chamado com ?format=html, retorna o HTML renderizado para
    facilitar debug em produção.
    """
    debug_html = request.GET.get("format") == "html"

    # 1) Dados iniciais
    logo_base64 = carregar_logo_base64()
    dados       = gerar_matriz_mensal(placa.strip().upper(), mes)
    dias        = list(range(1, 32))
    relacoes_id = relacionar_id_envio_por_dia(conectar_planilha())

    # 2) Constrói a matriz de respostas
    dados["resposta"] = construir_resposta_indexada(
        matriz_respostas=dados["matriz"],
        cabecalho=dados["cabecalho"],
        dias=dias
    )

    # 3) Converte assinatura para Base64 (se houver URL)
    _injetar_assinatura_b64(dados)

    # 4) Renderiza o HTML do relatório
    html_string = render_to_string(
        "relatorios/relatorio_mensal.html",
        {
            "dados":       dados,
            "dias":        dias,
            "logo_base64": logo_base64,
            "relacoes_id": relacoes_id,
        }
    )

    # 5) Modo debug: retorna HTML puro
    if debug_html:
        return HttpResponse(html_string, content_type="text/html")

    # 6) Debug opcional: grava o HTML em disco para inspeção
    try:
        with open("relatorio_debug.html", "w", encoding="utf-8") as f:
            f.write(html_string)
        logging.info("relatorio_debug.html gerado com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao gravar relatorio_debug.html: {e}")

    # 7) Converte em PDF e retorna resposta
    pdf_bytes = HTML(string=html_string).write_pdf()
    response  = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename  = f"relatorio_{dados['placa']}_{mes}.pdf"
    response["Content-Disposition"] = f"inline; filename={filename}"
    return response


def gerar_relatorio_mensal_completo_pdf(request, mes, ano):
    """
    Gera PDF contendo relatórios individuais de todas as placas no mês.
    """
    # 1) Dados iniciais
    logo_base64 = carregar_logo_base64()
    todos_raw, dias = gerar_matriz_mensal_completo(mes)
    relacoes_id = relacionar_id_envio_por_dia(conectar_planilha())

    # 2) Renderiza cada relatório em fragmentos de HTML
    placas_html = []
    for dados in todos_raw:
        # respostas
        resposta = construir_resposta_indexada(
            matriz_respostas=dados["matriz"],
            cabecalho=dados["cabecalho"],
            dias=dias
        )
        dados["resposta"] = resposta

        # assinatura em Base64
        _injetar_assinatura_b64(dados)

        # fragmento
        html_placa = render_to_string(
            "relatorios/relatorio_mensal_completo.html",
            {
                "dados":        dados,
                "dias":         dias,
                "logo_base64":  logo_base64,
                "relacoes_id":  relacoes_id,
                "quebra_pagina": True,
            }
        )
        placas_html.append(html_placa)

    # 3) Une as páginas e gera PDF
    combined_html = "\n".join(placas_html)

    # Debug: salva HTML completo (opcional)
    try:
        with open("relatorio_completo_debug.html", "w", encoding="utf-8") as f:
            f.write(combined_html)
        logging.info("relatorio_completo_debug.html gerado com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao gravar relatorio_completo_debug.html: {e}")

    pdf_bytes = HTML(string=combined_html).write_pdf()
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    filename = f"relatorio_mensal_completo_{mes}_{ano}.pdf"
    response["Content-Disposition"] = f"inline; filename={filename}"
    return response

def debug_relatorio_html(request, placa, mes):
    # monta tudo igual à view de PDF, mas retorna só o HTML:
    dados = gerar_matriz_mensal(placa.upper(), mes)
    dias = list(range(1,32))
    relacoes_id = relacionar_id_envio_por_dia(conectar_planilha())

    resposta = construir_resposta_indexada(
        matriz_respostas=dados["matriz"],
        cabecalho=dados["cabecalho"],
        dias=dias
    )
    dados["resposta"] = resposta
    _injetar_assinatura_b64(dados)
    logo_base64 = carregar_logo_base64()

    html = render_to_string("relatorios/relatorio_debug.html", {
        "dados":       dados,
        "dias":        dias,
        "logo_base64": logo_base64,
        "relacoes_id": relacoes_id,
    })
    return HttpResponse(html, content_type="text/html")

