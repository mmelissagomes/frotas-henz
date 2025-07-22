import gspread
import datetime
import unicodedata
from oauth2client.service_account import ServiceAccountCredentials

# 🔐 Conecta à planilha Google
def conectar_planilha():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials/henz-checklist-05aaeba03b3d.json", scope)
    cliente = gspread.authorize(credentials)
    planilha = cliente.open("relatorios-planilha-henz")
    return planilha.sheet1

# 🔧 Normaliza texto para evitar falhas na legenda
def normalizar_texto(valor):
    if not valor:
        return ""
    valor = unicodedata.normalize("NFKD", str(valor).strip())
    valor = valor.encode("ASCII", "ignore").decode("utf-8")
    return valor.lower()

# 📄 Gera matriz bruta para uma placa e mês específicos
def gerar_matriz_mensal(placa, mes):
    sheet = conectar_planilha()
    registros = sheet.get_all_records()
    cabecalho = sheet.row_values(1)
    perguntas_checklist = cabecalho[4:27]

    matriz = {pergunta: {} for pergunta in perguntas_checklist}
    observacoes = ""
    nome = ""
    imagem_base64 = ""
    assinatura = ""
    ano = ""

    for registro in registros:
        placa_atual = registro.get(cabecalho[2], "").strip().upper()
        if placa_atual != placa.upper():
            continue

        data_str = registro.get(cabecalho[3], "").strip()
        if "/" not in data_str:
            continue

        try:
            dia_str, mes_registro, ano_registro = data_str.split("/")
            dia = int(dia_str)
        except ValueError:
            continue

        if mes_registro != mes:
            continue

        for pergunta in perguntas_checklist:
            resposta = str(registro.get(pergunta, "")).strip()
            matriz[pergunta][dia] = resposta if resposta else "—"

        nome = registro.get(cabecalho[1], "").strip().upper()
        imagem_base64_atual = registro.get(cabecalho[28], "").strip()
        if not imagem_base64 and imagem_base64_atual:
            imagem_base64 = imagem_base64_atual

        assinatura = registro.get(cabecalho[29], "").strip()
        ano = ano_registro

        obs_extra = registro.get(cabecalho[27], "").strip() if len(cabecalho) > 27 else ""
        obs_final = registro.get(cabecalho[28], "").strip() if len(cabecalho) > 28 else ""
        observacoes += f"{data_str} — {obs_extra} {obs_final}\n"

    return {
        "matriz": matriz,
        "nome": nome,
        "placa": placa,
        "mes": mes,
        "ano": ano,
        "observacoes": observacoes,
        "imagem_base64": imagem_base64,
        "assinatura": assinatura,
        "cabecalho": cabecalho
    }

def gerar_matriz_mensal_completo(mes):
    sheet = conectar_planilha()
    registros = sheet.get_all_records()
    cabecalho = sheet.row_values(1)
    dias = list(range(1, 32))

    placas_encontradas = set()
    dados_por_placa = []

    for registro in registros:
        data_str = registro.get(cabecalho[3], "").strip()
        if "/" not in data_str:
            continue

        try:
            dia_str, mes_registro, ano_registro = data_str.split("/")
        except ValueError:
            continue

        if mes_registro != mes:
            continue

        placa = registro.get(cabecalho[2], "").strip().upper()
        if not placa or placa in placas_encontradas:
            continue

        placas_encontradas.add(placa)

        # ✅ Aqui reaproveitamos a função mensal que já está corrigida
        dados_raw = gerar_matriz_mensal(placa, mes)
        dados_por_placa.append(dados_raw)

    return dados_por_placa, dias



# 🧠 Constrói dicionário resposta indexado para uso no template
def construir_resposta_indexada(matriz_respostas, cabecalho, dias):
    perguntas_checklist = cabecalho[4:27]
    legenda_resposta = {
        "Conforme": "OK",
        "Não conforme": "NC",
        "Não aplicável": "N/A",
        "Não operadou": "NO",
        "": "—",
        None: "—"
    }

    resposta = {}
    for idx, pergunta_texto in enumerate(perguntas_checklist, start=4):
        resposta[idx] = {}
        for dia in dias:
            valor_raw = matriz_respostas.get(pergunta_texto, {}).get(dia, "")
            convertido = legenda_resposta.get(valor_raw, "—")
            resposta[idx][dia] = convertido
    return resposta

