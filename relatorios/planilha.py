import gspread
import unicodedata
import logging
from html import escape
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import urlparse
import base64
import requests


def is_image_url(url):
    path = urlparse(url).path.lower()
    return path.endswith((".png", ".jpg", ".jpeg"))




# Configura logging para toda a biblioteca
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s"
)


def conectar_planilha():
    """
    Autentica via Service Account e conecta na aba 1
    da planilha 'relatorios-planilha-henz'.
    """
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials/henz-checklist-05aaeba03b3d.json",
        scope
    )
    client = gspread.authorize(creds)
    return client.open("relatorios-planilha-henz").sheet1


def normalizar_texto(valor):
    """
    Remove acentos, HTML-escapa, une linhas, faz strip e uppercase.
    Usado para normalizar nomes e observações.
    """
    if not valor:
        return ""
    text = str(valor).strip()
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ASCII", "ignore").decode("utf-8")
    text = escape(text).replace("\n", " ").replace("\r", " ")
    return text.upper()


def _injetar_assinatura_url(dados):
    url = dados.get("assinatura", "").strip()
    if not url.lower().startswith(("http://", "https://")):
        logging.warning("Valor de assinatura não é uma URL")
        return
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        
        logging.info(f"🔎 Content-Type da assinatura: {content_type}")

        if not content_type.startswith("image/"):
            logging.warning(f"Tipo inesperado na assinatura: {content_type}")
            return

        b64 = base64.b64encode(resp.content).decode("utf-8")
        dados["assinatura"] = f"data:{content_type};base64,{b64}"
        logging.info(f"Assinatura embutida em base64 ({len(b64)} chars)")
    except Exception as e:
        logging.warning(f"Erro ao baixar assinatura de {url}: {e}")
        dados["assinatura"] = ""  # garantir que valor inválido não fique pendente

def obter_assinatura_url(registro, cabecalho, idx):
    nome_assinatura = cabecalho[29]
    assinatura_url = str(registro.get(nome_assinatura, "")).replace("\n", "").strip()

    if assinatura_url.startswith(("http://", "https://")) and is_image_url(assinatura_url):
        logging.info(f"🖼️ Assinatura encontrada na linha {idx}: {assinatura_url}")
        return assinatura_url
    else:
        logging.debug(f"Linha {idx} sem assinatura válida")
        return ""


def gerar_matriz_mensal(placa, mes):
    """
    Retorna um dict com:
      - matriz: respostas brutas por pergunta e dia
      - nome, placa, mês, ano
      - observacoes (concatenadas)
      - imagem_base64 (marca d’água)
      - assinatura (URL bruta)
      - cabecalho (lista de nomes de colunas)
    """
    logging.info(f"🔍 Gerando matriz para placa={placa}, mês={mes}")
    sheet = conectar_planilha()
    registros = sheet.get_all_records()
    cabecalho = sheet.row_values(1)
    

    # perguntas nas colunas 5 a 27 (índices 4–26)
    perguntas = cabecalho[4:27]

    matriz       = {pergunta: {} for pergunta in perguntas}
    observacoes  = []
    nome         = ""
    imagem_base64= ""
    assinatura   = ""
    ano          = ""

    for idx, registro in enumerate(registros, start=2):
        try:
            placa_bd = str(registro.get(cabecalho[2], "")).strip().upper()
            if placa_bd != placa.upper():
                continue

            data_str = str(registro.get(cabecalho[3], "")).strip()
            if "/" not in data_str:
                continue
            dia_str, mes_bd, ano_bd = data_str.split("/")
            if mes_bd != mes:
                continue
            dia = int(dia_str)

            # popula matriz de respostas
            for col_idx, pergunta in enumerate(perguntas, start=4):
                raw = str(registro.get(pergunta, "")).strip()
                valor = f"{raw}:{col_idx}:{dia}" if raw else "—"
                matriz[pergunta][dia] = valor

            # pega nome (normalize)
            if not nome:
                nome = normalizar_texto(registro.get(cabecalho[1], ""))

            # marca d’água (base64) – primeira não vazia
            if not imagem_base64:
                marca = registro.get(cabecalho[28], "").strip()
                if marca:
                    imagem_base64 = marca

            # URL da assinatura (coluna 30, índice 29)
            assinatura = obter_assinatura_url(registro, cabecalho, idx)
            if assinatura:
                dados_temp = {"assinatura": assinatura}
            _injetar_assinatura_url(dados_temp)
            assinatura = dados_temp["assinatura"]


            # observações (coluna 28, índice 27)
            obs = str(registro.get(cabecalho[27], "")).strip()
            if obs:
                observacoes.append(f"{data_str} — {obs}")
                

            ano = ano_bd
        
        except Exception as e:
            logging.error(f"Erro no registro {idx}: {e}")

            

    return {
        "matriz":        matriz,
        "nome":          nome,
        "placa":         placa.upper(),
        "mes":           mes,
        "ano":           ano,
        "observacoes":   "\n".join(observacoes),
        "imagem_base64": imagem_base64,
        "assinatura":    assinatura,
        "cabecalho":     cabecalho,
    }


def gerar_matriz_mensal_completo(mes):
    """
    Para cada placa única no mês, chama gerar_matriz_mensal
    e retorna lista de dicts + lista de dias (1–31).
    """
    sheet = conectar_planilha()
    todos = sheet.get_all_records()
    cabecalho = sheet.row_values(1)
    dias = list(range(1, 32))

    placas = set()
    resultados = []

    for idx, registro in enumerate(todos, start=2):
        data_str = str(registro.get(cabecalho[3], "")).strip()
        if "/" not in data_str:
            continue
        _, mes_bd, _ = data_str.split("/")
        if mes_bd != mes:
            continue

        placa_bd = str(registro.get(cabecalho[2], "")).strip().upper()
        if not placa_bd or placa_bd in placas:
            continue

        placas.add(placa_bd)
        resultados.append(gerar_matriz_mensal(placa_bd, mes))

    return resultados, dias


def construir_resposta_indexada(matriz_respostas, cabecalho, dias):
    """
    Converte valores brutos (e.g. "Conforme:4:13")
    em siglas: OK, NC, N/A, NO, ou “—”.
    Retorna dict int->(dict dia->sigla).
    """
    perguntas = cabecalho[4:27]
    legenda = {
        "Conforme":      "OK",
        "Não conforme":  "NC",
        "Não aplicável": "N/A",
        "Não operadou":  "NO",
        "":               "—",
        None:            "—",
    }

    indexado = {}
    for col_idx, pergunta in enumerate(perguntas, start=4):
        indexado[col_idx] = {}
        for dia in dias:
            bruto = matriz_respostas.get(pergunta, {}).get(dia, "")
            base = bruto.split(":", 1)[0] if ":" in bruto else bruto
            indexado[col_idx][dia] = legenda.get(base, "—")
    return indexado


def relacionar_id_envio_por_dia(sheet):
    """
    Lê toda a planilha e retorna lista de dicts:
    {"id_envio": "<texto>", "dia": <int>}
    usando coluna 31 (índice 30) como ID de envio
    e coluna 4 (índice 3) como data.
    """
    registros = sheet.get_all_records()
    cabecalho = sheet.row_values(1)

    if len(cabecalho) <= 30:
        logging.warning(f"A planilha tem apenas {len(cabecalho)} colunas; não achei coluna 31")
        return []

    nome_id = cabecalho[30]
    nome_data = cabecalho[3]
    relacoes = []

    for idx, reg in enumerate(registros, start=2):
        raw_id = str(reg.get(nome_id, "")).strip()
        data_str = str(reg.get(nome_data, "")).strip()
        if "/" not in data_str or not raw_id:
            continue

        try:
            dia = int(data_str.split("/")[0])
        except ValueError:
            logging.warning(f"Dia inválido na linha {idx}: {data_str}")
            continue

        relacoes.append({"id_envio": raw_id, "dia": dia})
        logging.debug(f"-> Linha {idx}: id_envio={raw_id}, dia={dia}")

    return relacoes
