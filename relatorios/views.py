import os
from pathlib import Path
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

BASE_DIR = Path(__file__).resolve().parent.parent

@login_required
def relatorio(request):
    # 🔑 Autenticação com Google Sheets
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        os.path.join(BASE_DIR, 'credentials', 'henz-checklist.json'),
        scope
    )
    client = gspread.authorize(creds)

    # 📄 Conectar à planilha
    sheet = client.open('Checklist Diários').sheet1
    registros = sheet.get_all_records()
    df = pd.DataFrame(registros)

    # 🔎 Filtros
    placa = request.GET.get('placa')
    funcionario = request.GET.get('funcionario')
    mes = request.GET.get('mes')

    if placa:
        df = df[df['Placa'] == placa]
    if funcionario:
        df = df[df['Funcionário'] == funcionario]
    if mes:
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        df = df[df['Data'].dt.month == int(mes)]

    dados_filtrados = df.to_dict(orient='records')

    return render(request, 'relatorios/home.html', {'dados': dados_filtrados})