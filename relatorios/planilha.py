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

    # Inicializa matriz vazia para cada pergunta
    matriz = {pergunta: {} for pergunta in perguntas_checklist}
    observacoes = ""
    nome = ""
    imagem_base64 = ""
    assinatura = ""
    ano = ""

    for idx, registro in enumerate(registros, start=2):
        try:
            placa_atual = str(registro.get(cabecalho[2], "")).strip().upper()
            if placa_atual != placa.upper():
                continue

            data_str = str(registro.get(cabecalho[3], "")).strip()
            if "/" not in data_str:
                continue

            dia_str, mes_registro, ano_registro = data_str.split("/")
            if mes_registro != mes:
                continue

            dia = int(dia_str)

            # ========= LOOP DE PERGUNTAS MOVIDO PRA CÁ =========
            for idx_pergunta, pergunta in enumerate(perguntas_checklist, start=4):
                resposta_raw = str(registro.get(pergunta, "")).strip()  # mantemos exatamente como no BD

                if resposta_raw:
                    valor_formatado = f"{resposta_raw}:{idx_pergunta}:{dia}"
                else:
                    valor_formatado = "—"

                matriz[pergunta][dia] = valor_formatado
            # ===================================================

            # Preenche dados adicionais somente uma vez por registro válido
            nome = normalizar_texto(registro.get(cabecalho[1], ""))

            # Imagem base64 para marca d'água (primeira encontrada)
            imagem_base64_atual = registro.get(cabecalho[28], "").strip()
            if not imagem_base64 and imagem_base64_atual:
                imagem_base64 = imagem_base64_atual

            # ✅ Assinatura como imagem (Jotform)
            assinatura_raw = str(registro.get(cabecalho[29], "")).strip()
            if assinatura_raw.startswith("http") and any(ext in assinatura_raw for ext in (".png", ".jpg", ".jpeg")):
                assinatura = assinatura_raw
                logging.info(f"🖼️ Assinatura recebida como imagem: {assinatura}")
            else:
                assinatura = "—"
                logging.warning(f"⚠️ Assinatura inválida ou ausente: {assinatura_raw}")

            ano = ano_registro

            obs_extra = registro.get(cabecalho[27], "").strip()
            if obs_extra:
                observacoes += f"{data_str} — {obs_extra}\n"

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

    for idx, registro in enumerate(registros, start=2):
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
            # Reusa a função mensal para cada placa encontrada
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

    resposta_indexada = {}
    for idx_coluna, pergunta in enumerate(perguntas_checklist, start=4):
        resposta_indexada[idx_coluna] = {}
        for dia in dias:
            valor_formatado = matriz_respostas.get(pergunta, {}).get(dia, "")
            # extrai a parte antes dos dois-pontos
            resposta_base = valor_formatado.split(":", 1)[0] if ":" in valor_formatado else valor_formatado
            resposta_indexada[idx_coluna][dia] = legenda_resposta.get(resposta_base, "—")
    return resposta_indexada

# 🔗 Relaciona ID de envio (coluna 30) com dia
def relacionar_id_envio_por_dia(sheet):
    registros = sheet.get_all_records()
    cabecalho = sheet.row_values(1)

    # Garanta que exista COLUNA 30 (índice 29)
    if len(cabecalho) <= 29:
        logging.warning(f"⚠️ A planilha tem apenas {len(cabecalho)} colunas, coluna 30 não encontrada.")
        return []

    nome_id_envio = cabecalho[30]
    nome_data      = cabecalho[3]

    relacoes = []
    for idx, registro in enumerate(registros, start=2):
        id_envio = str(registro.get(nome_id_envio, "")).strip()
        data_str = str(registro.get(nome_data, ""),).strip()

        if "/" not in data_str:
            logging.warning(f"⚠️ Data malformada na linha {idx}: {data_str}")
            continue

        try:
            dia = int(data_str.split("/")[0])
        except ValueError:
            logging.warning(f"⚠️ Dia inválido na linha {idx}: {data_str}")
            continue

        if id_envio:
            relacoes.append({"id_envio": id_envio, "dia": dia})
            logging.info(f"📦 Linha {idx}: ID={id_envio}, Dia={dia}")
        else:
            logging.warning(f"⚠️ ID ausente na linha {idx}")

    return relacoes
