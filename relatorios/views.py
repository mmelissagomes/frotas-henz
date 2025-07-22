from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from .planilha import (
    gerar_matriz_mensal,
    gerar_matriz_mensal_completo,
    construir_resposta_indexada
)
from django.shortcuts import render
import base64
from datetime import datetime


def carregar_logo_base64():
    caminho_logo = "blog/static/images/logo.png"
    with open(caminho_logo, "rb") as img_file:
        base64_string = base64.b64encode(img_file.read()).decode("utf-8")
        return "data:image/png;base64," + base64_string


def pagina_relatorios(request):
    meses = [
        ("01", "Janeiro"), ("02", "Fevereiro"), ("03", "Março"),
        ("04", "Abril"), ("05", "Maio"), ("06", "Junho"),
        ("07", "Julho"), ("08", "Agosto"), ("09", "Setembro"),
        ("10", "Outubro"), ("11", "Novembro"), ("12", "Dezembro")
    ]
    ano_atual = datetime.now().year
    anos = [str(ano) for ano in range(2022, ano_atual + 1)]

    return render(request, "relatorios/index.html", {
        "months": meses,
        "years": anos
    })


def gerar_relatorio_mensal_pdf(request, placa, mes):
    logo_base64 = carregar_logo_base64()
    dados = gerar_matriz_mensal(placa.strip().upper(), mes)
    dias = list(range(1, 32))

    resposta = construir_resposta_indexada(
        matriz_respostas=dados.get("matriz", {}),
        cabecalho=dados.get("cabecalho", []),
        dias=dias
    )
    dados["resposta"] = resposta

    html_string = render_to_string("relatorios/relatorio_mensal.html", {
        "dados": dados,
        "dias": dias,
        "logo_base64": logo_base64,
        "resposta": dados["resposta"],
    })

    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    filename = f"relatorio_{dados['placa']}_{mes}.pdf"
    response["Content-Disposition"] = f"inline; filename={filename}"
    return response


def gerar_relatorio_mensal_completo_pdf(request, mes, ano):
    todos_raw, dias = gerar_matriz_mensal_completo(mes)
    logo_base64 = carregar_logo_base64()
    placas_html = []

    for dados in todos_raw:
        resposta = construir_resposta_indexada(
            matriz_respostas=dados.get("matriz", {}),
            cabecalho=dados.get("cabecalho", []),
            dias=dias
        )
        dados["resposta"] = resposta

        html_placa = render_to_string("relatorios/relatorio_mensal_completo.html", {
            "dados": dados,
            "dias": dias,
            "logo_base64": logo_base64,
            "resposta": dados["resposta"],
            "quebra_pagina": True
        })
        placas_html.append(html_placa)

    html_string = "\n".join(placas_html)

    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type="application/pdf")
    filename = f"relatorio_mensal_completo_{mes}.pdf"
    response["Content-Disposition"] = f"inline; filename={filename}"
    return response

