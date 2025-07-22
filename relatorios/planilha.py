import gspread
import datetime
import unicodedata
import logging
from html import escape
from oauth2client.service_account import ServiceAccountCredentials

# 🪵 Configura logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)

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

# 🔧 Normaliza e sanitiza texto
def normalizar_texto(valor):
    if not valor:
        return ""
    valor = unicodedata.normalize("NFKD", str(valor).strip())
    valor = valor.encode("ASCII", "ignore").decode("utf-8")
    valor = escape(valor).replace('\n', ' ').replace('\r', ' ')
    return valor.upper()

# 📄 Gera matriz mensal para uma placa e mês
def gerar_matriz_mensal(placa, mes):
    logging.info(f"🔍 Gerando matriz para placa: {placa}, mês: {mes}")
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

    for idx, registro in enumerate(registros):
        try:
            placa_atual = str(registro.get(cabecalho[2], "")).strip().upper()
            if placa_atual != placa.upper():
                continue

            data_str = str(registro.get(cabecalho[3], "")).strip()
            if "/" not in data_str:
                continue

            dia_str, mes_registro, ano_registro = data_str.split("/")
            dia = int(dia_str)

            if mes_registro != mes:
                continue

            for idx_pergunta, pergunta in enumerate(perguntas_checklist, start=4):
                resposta_raw = str(registro.get(pergunta, "")).strip()
                resposta = normalizar_texto(resposta_raw)

                if resposta:
                    valor_formatado = f"{resposta}:{idx_pergunta}:{dia}"
                else:
                    valor_formatado = "—"

            matriz[pergunta][dia] = valor_formatado


            nome = normalizar_texto(registro.get(cabecalho[1], ""))
            imagem_base64_atual = registro.get(cabecalho[28], "").strip()
            if not imagem_base64 and imagem_base64_atual:
                imagem_base64 = imagem_base64_atual

            # ✅ Assinatura como imagem (Jotform)
            assinatura_raw = str(registro.get(cabecalho[29], "")).strip()
            if assinatura_raw.startswith("http") and (
                ".png" in assinatura_raw or ".jpg" in assinatura_raw or ".jpeg" in assinatura_raw
            ):
                assinatura = assinatura_raw
                logging.info(f"🖼️ Assinatura recebida como imagem: {assinatura}")
            else:
                assinatura = "—"
                logging.warning(f"⚠️ Assinatura inválida ou ausente: {assinatura_raw}")

            ano = ano_registro

            obs_extra = registro.get(cabecalho[27], "") if len(cabecalho) > 27 else ""
            obs_final = registro.get(cabecalho[28], "") if len(cabecalho) > 28 else ""
            observacoes += f"{data_str} — {obs_extra} {obs_final}\n"

        except Exception as e:
            logging.error(f"❌ Erro no registro {idx}: {e}")

    return {
        "matriz": matriz,
        "nome": nome,
        "placa": placa,
        "mes": mes,
        "ano": ano,
        "observacoes": observacoes.strip(),
        "imagem_base64": imagem_base64,
        "assinatura": assinatura,
        "cabecalho": cabecalho
    }

# 📦 Gera matriz mensal para todas as placas no mês
def gerar_matriz_mensal_completo(mes):
    sheet = conectar_planilha()
    registros = sheet.get_all_records()
    cabecalho = sheet.row_values(1)
    dias = list(range(1, 32))

    placas_encontradas = set()
    dados_por_placa = []

    for idx, registro in enumerate(registros):
        try:
            data_str = str(registro.get(cabecalho[3], "")).strip()
            if "/" not in data_str:
                continue
            dia_str, mes_registro, ano_registro = data_str.split("/")

            if mes_registro != mes:
                continue

            placa = str(registro.get(cabecalho[2], "")).strip().upper()
            if not placa or placa in placas_encontradas:
                continue

            placas_encontradas.add(placa)
            dados_raw = gerar_matriz_mensal(placa, mes)
            dados_por_placa.append(dados_raw)

        except Exception as e:
            logging.error(f"❌ Erro ao processar registro {idx}: {e}")

    return dados_por_placa, dias

# 🧠 Constrói dicionário de respostas indexadas
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
            parte_resposta = valor_raw.split(":")[0] if ":" in valor_raw else valor_raw
            convertido = legenda_resposta.get(parte_resposta, "—")
            resposta[idx][dia] = convertido
    return resposta

def relacionar_id_envio_por_dia(sheet):

        registros = sheet.get_all_records()
        cabecalho = sheet.row_values(1)

        if len(cabecalho) < 30:
            logging.warning(f"⚠️ A planilha possui apenas {len(cabecalho)} colunas. Coluna 30 não encontrada.")
            return []

        nome_id_envio = cabecalho[30]   # Coluna 30 (índice 29)
        nome_data = cabecalho[3]        # Coluna 4 (índice 3)

        relacoes = []

        for idx, registro in enumerate(registros):
            id_envio = str(registro.get(nome_id_envio, "")).strip()
            data_str = str(registro.get(nome_data, "")).strip()

            if "/" in data_str:
                try:
                    dia_str, _, _ = data_str.split("/")
                    dia = int(dia_str)
                except ValueError:
                    dia = None
                    logging.warning(f"⚠️ Data malformada no registro {idx+2}: {data_str}")
            else:
                dia = None

            if id_envio and dia:
                relacoes.append({
                    "id_envio": id_envio,
                    "dia": dia
                })
                logging.info(f"📦 Registro {idx+2}: ID={id_envio}, Dia={dia}")
            else:
                logging.warning(f"⚠️ Registro {idx+2} incompleto ou inválido: ID={id_envio}, Data={data_str}")
            sheet = conectar_planilha()
            relacoes = relacionar_id_envio_por_dia(sheet)
            for r in relacoes:
                return relacoes

            
 
