import pyautogui, subprocess, PyPDF2, tempfile, shutil
import time, os, random, re, io, base64, logging, uuid
from tenacity import retry, stop_after_attempt, wait_fixed
from pathlib import Path
from pymongo import MongoClient
import pyperclip
from dotenv import load_dotenv

load_dotenv()

# Logging 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Configurações globais
pyautogui.FAILSAFE = False

URL                 = os.getenv("URL_SITE")
FOLDER_PATH         = os.path.join(os.path.dirname(__file__), "imgs")
EXTENSAO_PATH       = os.path.join(os.path.dirname(__file__), "iproyal_proxy")
CHROME_EXE          = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DOWNLOADS           = Path.home() / "Downloads"

PROXY_HOST          = os.getenv("PROXY_HOST", "geo.iproyal.com")
PROXY_PORT          = int(os.getenv("PROXY_PORT", 12321))
PROXY_USERNAME      = os.getenv("PROXY_USERNAME", "")
PROXY_PASSWORD_BASE = os.getenv("PROXY_PASSWORD", "")   # ex: "senha_country-br"

# MongoDB
MONGO_URI  = os.getenv("URI_WISE")
CLIENT     = MongoClient(MONGO_URI)
DATABASE   = CLIENT["RECEITA_FEDERAL"]
COLLECTION = DATABASE["CAFIR"]

# Rotação de IP (session-id no IPRoyal)

def gerar_session_id() -> str:
    """Gera um ID de sessão aleatório para forçar novo IP no proxy rotativo."""
    return uuid.uuid4().hex[:12]


def gerar_password_com_session(session_id: str) -> str:
    """
    IPRoyal aceita parâmetros extras no password:
      senha_country-br_session-XXXX
    Isso garante IP diferente a cada nova sessão.
    """
    base = PROXY_PASSWORD_BASE
    # Remove session anterior se existir
    base = re.sub(r"_session-[a-f0-9]+", "", base)
    return f"{base}_session-{session_id}"


def regenerar_extensao_proxy(session_id: str | None = None):
    """
    Regera o background.js da extensão Chrome com as credenciais do .env,
    opcionalmente trocando o session-id para rotacionar o IP.
    """
    sid      = session_id or gerar_session_id()
    password = gerar_password_com_session(sid)

    background = f"""
const config = {{
    mode: "fixed_servers",
    rules: {{
        singleProxy: {{
            scheme: "http",
            host: "{PROXY_HOST}",
            port: {PROXY_PORT}
        }}
    }}
}};

chrome.proxy.settings.set({{ value: config, scope: "regular" }});

chrome.webRequest.onAuthRequired.addListener(
    () => ({{
        authCredentials: {{
            username: "{PROXY_USERNAME}",
            password: "{password}"
        }}
    }}),
    {{ urls: ["<all_urls>"] }},
    ["asyncBlocking"]
);
"""
    bg_path = os.path.join(EXTENSAO_PATH, "background.js")
    with open(bg_path, "w", encoding="utf-8") as f:
        f.write(background)

    log.info(f"[PROXY] Extensão atualizada — session-id: {sid}  host: {PROXY_HOST}:{PROXY_PORT}")
    return sid


# Utilitários de tela

@retry(stop=stop_after_attempt(10), wait=wait_fixed(0.5),
       retry_error_callback=lambda retry_state: None)
def localizar_imagem(imagem, confidence=0.7, grayscale=False):
    return pyautogui.locateCenterOnScreen(
        imagem,
        confidence=confidence,
        grayscale=grayscale,
    )


def clicar_em(position, variacao_x=8, variacao_y=4):
    """Move e clica com pequena variação humanizada."""
    x = position.x + random.randint(-variacao_x, variacao_x)
    y = position.y + random.randint(-variacao_y, variacao_y)
    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))
    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.click()
    time.sleep(random.uniform(0.3, 0.8))


def digitar_humanizado(texto: str, intervalo_min: float = 0.04, intervalo_max: float = 0.15):
    for caractere in texto:
        pyautogui.write(caractere, interval=random.uniform(intervalo_min, intervalo_max))


def esperar_download(file_path: str, timeout: int = 60) -> bool:
    """
    Aguarda o arquivo PDF aparecer no diretório de downloads.
    Também verifica que não existe versão .crdownload pendente.
    """
    crdownload = file_path + ".crdownload"
    inicio = time.time()
    while time.time() - inicio < timeout:
        if os.path.exists(file_path) and not os.path.exists(crdownload):
            return True
        time.sleep(0.5)
    return False


# Chrome via subprocess

def abrir_chrome(url: str, processo=None, usar_proxy: bool = True, session_id: str | None = None) -> subprocess.Popen:
    """
    Fecha o processo Chrome anterior (se existir) e abre um novo.
    Se usar_proxy=True, regera a extensão com novo session-id antes de abrir.
    """
    # Fecha processo anterior
    if processo and processo.poll() is None:
        log.info("[CHROME] Encerrando instância anterior...")
        processo.terminate()
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            processo.kill()

    # Novo perfil temporário por sessão (evita estado compartilhado)
    perfil_temp = tempfile.mkdtemp(prefix="chrome_rpa_")

    args = [
        CHROME_EXE,
        f"--user-data-dir={perfil_temp}",
        "--start-maximized",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-infobars",
    ]

    if usar_proxy:
        sid = regenerar_extensao_proxy(session_id)
        args.insert(1, f"--load-extension={EXTENSAO_PATH}")
        log.info(f"[CHROME] Abrindo COM proxy — session: {sid}")
    else:
        log.info("[CHROME] Abrindo SEM proxy")

    args.append(url)

    novo_processo = subprocess.Popen(args)
    # Guarda o caminho do perfil temporário no objeto para limpeza posterior
    novo_processo._perfil_temp = perfil_temp  # type: ignore[attr-defined]

    time.sleep(3)
    aceitar_cookies()

    return novo_processo


def fechar_chrome(processo):
    """Encerra o Chrome e limpa o perfil temporário."""
    if processo and processo.poll() is None:
        processo.terminate()
        try:
            processo.wait(timeout=5)
        except subprocess.TimeoutExpired:
            processo.kill()

    perfil = getattr(processo, "_perfil_temp", None)
    if perfil and os.path.exists(perfil):
        shutil.rmtree(perfil, ignore_errors=True)
        log.info(f"[CHROME] Perfil temporário removido: {perfil}")


# Fluxo de automação

def aceitar_cookies() -> bool:
    time.sleep(random.uniform(1.5, 2.8))
    position = localizar_imagem(os.path.join(FOLDER_PATH, "1-aceitar_cookies.png"), confidence=0.7)
    if position is None:
        log.warning("Botão de aceitar cookies não encontrado.")
        return False
    clicar_em(position)
    return True


def pesquisar_cib(cib: str) -> bool:
    position = localizar_imagem(os.path.join(FOLDER_PATH, "2-informa_cib.png"), confidence=0.7)
    if not position:
        log.warning("Campo de pesquisa CIB não encontrado.")
        return False
    clicar_em(position)
    digitar_humanizado(cib)

    position = localizar_imagem(os.path.join(FOLDER_PATH, "3-emitir_certidao.png"), confidence=0.7)
    if not position:
        log.warning("Botão de emitir certidão não encontrado.")
        return False
    clicar_em(position)
    return True


def fazer_nova_consulta() -> bool:
    pyautogui.press("end")
    time.sleep(0.5)
    position = localizar_imagem(os.path.join(FOLDER_PATH, "10-nova_consulta.png"), confidence=0.7)
    if not position:
        log.warning("Botão de nova consulta não encontrado.")
        return False
    clicar_em(position)
    return True


def verificar_certidao_valida_encontrada(cib: str) -> bool | None:
    position = localizar_imagem(os.path.join(FOLDER_PATH, "4-certidao_valida_encontrada.png"), confidence=0.7)
    if not position:
        log.info(f"[{cib}] Certidão válida NÃO encontrada.")
        return False

    position = localizar_imagem(os.path.join(FOLDER_PATH, "5-consultar_certidao.png"), confidence=0.7)
    if not position:
        log.warning(f"[{cib}] Botão consultar certidão não encontrado.")
        return None

    # Offset para evitar clicar no centro exato (anti-bot)
    x = position.x + random.randint(-8, 8) - position.x / 4
    y = position.y + random.randint(-4, 4)
    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))
    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.click()
    time.sleep(random.uniform(0.3, 0.8))

    time.sleep(random.uniform(1.5, 2.8))
    pyautogui.scroll(-200)
    time.sleep(0.5)

    # Filtrar por data de validade
    position = localizar_imagem(os.path.join(FOLDER_PATH, "6-data_validade.png"), confidence=0.7)
    if not position:
        log.warning(f"[{cib}] Filtro de data de validade não encontrado.")
        return None
    clicar_em(position)
    pyautogui.scroll(-200)
    time.sleep(0.5)

    # Consultar certidão válida
    position = localizar_imagem(os.path.join(FOLDER_PATH, "7-consultar_certidao.png"), confidence=0.7)
    if not position:
        log.warning(f"[{cib}] Botão consultar certidão (2) não encontrado.")
        return None
    clicar_em(position)
    pyautogui.scroll(-200)
    time.sleep(0.5)

    # Tenta baixar 2ª via
    try:
        resultados = list(pyautogui.locateAllOnScreen(
            os.path.join(FOLDER_PATH, "8-baixar_2_via.png"), confidence=0.7))
        if not resultados:
            raise ValueError("Botão '8-baixar_2_via' não encontrado")

        position = pyautogui.center(resultados[0])
        clicar_em(position, variacao_x=4, variacao_y=4)

    except Exception:
        # Fallback: tentar pela imagem '11-valida'
        resultados = list(pyautogui.locateAllOnScreen(
            os.path.join(FOLDER_PATH, "11-valida.png"), confidence=0.7))
        if not resultados:
            log.warning(f"[{cib}] Certidão válida (fallback) não encontrada.")
            return None

        position = pyautogui.center(resultados[0])
        clicar_em(position, variacao_x=4, variacao_y=4)

        pyautogui.press("tab")
        time.sleep(0.2)
        pyautogui.press("enter")
        time.sleep(0.5)

    pyautogui.scroll(500)
    time.sleep(0.5)
    return True


# Captura de mensagem de erro do site

def capturar_mensagem(cib: str) -> str | None:
    pyautogui.press("end")
    time.sleep(0.5)

    largura, altura = pyautogui.size()
    pyautogui.moveTo(largura / 2, altura - 200, duration=random.uniform(0.3, 0.8))
    pyautogui.click()
    time.sleep(random.uniform(0.2, 0.4))

    pyautogui.hotkey("ctrl", "a")
    time.sleep(random.uniform(0.3, 0.8))
    pyautogui.hotkey("ctrl", "c")
    time.sleep(random.uniform(0.3, 0.8))

    texto = pyperclip.paste()
    lines = [line.strip() for line in texto.split("\n") if line.strip()]
    cib_line = f"{cib[:1]}.{cib[1:4]}.{cib[4:7]}-{cib[7:10]}"
    start_line = next((i for i, l in enumerate(lines) if cib_line in l), None)
    end_line   = next((i for i, l in enumerate(lines) if l.lower().startswith("avaliar serviço")), None)

    if start_line is None or end_line is None:
        return None

    texto = "\n".join(lines[start_line + 1:end_line])
    pyautogui.moveTo(largura / 2, altura - 200, duration=random.uniform(0.1, 0.4))
    pyautogui.click()
    return texto


# Parse do PDF

def get_line(lines: list[str], name: str) -> str | None:
    for line in lines:
        if name in line.lower():
            return line
    return None


def parse_pdf(file_path: str, cib: str) -> dict | None:
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        pdf   = PyPDF2.PdfReader(io.BytesIO(content))
        lines = pdf.pages[0].extract_text().split("\n")
        lines = [l.replace("\xa0", " ").strip() for l in lines]

        data: dict = {"CIB": cib, "PDF": base64.b64encode(content).decode()}

        line = get_line(lines, "nome do imóvel")
        if line:
            data["NM_IMOVEL"] = line.split(":")[1].strip()

        line = get_line(lines, "município")
        if line:
            data["NM_MUNICIPIO"] = line.split(":")[1]
            if data["NM_MUNICIPIO"].endswith(" UF"):
                data["NM_MUNICIPIO"] = data["NM_MUNICIPIO"].replace(" UF", "")
            data["UF"] = line.split(":")[2].strip()

        line = get_line(lines, "área total (em hectares):")
        if line:
            data["AREA_TOTAL"] = float(re.sub(r"[^0-9,]", "", line).replace(",", "."))

        line = get_line(lines, "contribuinte:")
        if line:
            data["NM_CONTRIBUINTE"] = line.split(":")[1].strip()

        line = get_line(lines, "cpf:")
        if line:
            data["IN_CPF"]    = True
            data["CPF_CNPJ"]  = re.sub(r"\D", "", line)
        else:
            line = get_line(lines, "cnpj:")
            if line:
                data["IN_CPF"]   = False
                data["CPF_CNPJ"] = re.sub(r"\D", "", line)

        line = get_line(lines, "emitida às ")
        if line:
            data["DT_EMISSAO"] = (
                line.replace("Emitida às ", "")
                    .replace("<hora e data de Brasília>.", "")
                    .replace(" do dia ", " ")
                    .strip()
            )

        line = get_line(lines, "válida até ")
        if line:
            data["DT_VALIDADE"] = line.replace("Válida até ", "").strip()[:-1]

        line = get_line(lines, "código de controle da certidão: ")
        if line:
            data["CODIGO_CERTIDAO"] = line.replace("Código de controle da certidão:", "").strip()

        return data

    except Exception as e:
        log.error(f"[{cib}] Erro ao extrair dados do PDF: {e}")
        return None

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# Extração principal por CIB

def extract_cib(cib: str, chrome: subprocess.Popen | None = None, fechar_chrome: bool = True) -> tuple[dict | None, str | None]:
    data, texto = None, None

    if not chrome:
        chrome = abrir_chrome(URL)

    ok = pesquisar_cib(cib)
    if not ok:
        return None, None

    baixou = verificar_certidao_valida_encontrada(cib)
    file_path = str(DOWNLOADS / f"Certidao-{cib}.pdf")

    if baixou is False:
        texto = capturar_mensagem(cib)
        if "sucesso" in str(texto).lower():
            baixou = True

    if baixou or baixou is None:
        if esperar_download(file_path, timeout=30):
            data = parse_pdf(file_path, cib)
        if not data:
            texto = capturar_mensagem(cib)

    if fechar_chrome:
        fechar_chrome(chrome)

    return data, texto


def main():
    CLIENT_AGRO = None
    processo    = None
    usar_proxy  = False   # começa sem proxy; rotaciona a cada N CIBs
    session_id  = None
    ROTACIONAR_A_CADA = 10  # troca IP a cada N consultas

    try:
        CLIENT_AGRO         = MongoClient(os.getenv("URI_AGRO"))
        DATABASE_AGRO       = CLIENT_AGRO["AGRONEGOCIO"]
        COLLECTION_AGRO     = DATABASE_AGRO["CAFIR_ld"]
        COLLECTION_AGRO_PDF = DATABASE_AGRO["CAFIR_PDF_ld"]
        COLLECTION_AGRO_ERR = DATABASE_AGRO["CAFIR_ERROR_ld"]

        # Carrega CIBs pendentes
        docs       = COLLECTION.find({"SG_UF": "SC", "NR_IMOVEL": {"$ne": None}}, {"_id": 0, "NR_IMOVEL": 1})
        cibs_cafir = [d["NR_IMOVEL"] for d in docs]

        docs       = COLLECTION_AGRO.find({"UF": "SC", "CIB": {"$ne": None}}, {"_id": 0, "CIB": 1})
        cibs_ok    = {d["CIB"] for d in docs}

        docs       = COLLECTION_AGRO_ERR.find({"CIB": {"$ne": None}}, {"_id": 0, "CIB": 1})
        cibs_err   = {d["CIB"] for d in docs}

        cibs = list(set(cibs_cafir) - cibs_ok - cibs_err)
        log.info(f"{len(cibs)} CIBs pendentes para processar")

        # Abre Chrome inicial
        processo = abrir_chrome(URL, usar_proxy=usar_proxy)

        for index, cib in enumerate(cibs):
            log.info(f"[{index + 1}/{len(cibs)}] Processando CIB: {cib}")

            data, texto = extract_cib(cib, chrome=processo, fechar_chrome=False)

            # Salva resultado
            if not data:
                if texto and not str(texto).lower().startswith("período"):
                    try:
                        COLLECTION_AGRO_ERR.insert_one({"CIB": cib, "ERRO": texto})
                        log.warning(f"[{cib}] Salvo como erro: {str(texto)[:80]}")
                    except Exception as db_err:
                        log.error(f"[{cib}] Falha ao registrar erro no banco: {db_err}")
            else:
                try:
                    COLLECTION_AGRO_PDF.insert_one({"CPF_CNPJ": data.get("CPF_CNPJ"), "PDF": data["PDF"]})
                    data_without_pdf = {k: v for k, v in data.items() if k != "PDF"}
                    COLLECTION_AGRO.insert_one(data_without_pdf)
                    log.info(f"[{cib}] ✓ Dados salvos com sucesso")
                except Exception as db_err:
                    log.error(f"[{cib}] Falha ao salvar no banco: {db_err}")

            # Rotaciona IP / reabre Chrome
            deve_rotacionar = ((index + 1) % ROTACIONAR_A_CADA == 0)
            nova_consulta_ok = fazer_nova_consulta()

            if deve_rotacionar or not nova_consulta_ok:
                usar_proxy = True          # sempre usa proxy ao rotacionar
                session_id = gerar_session_id()
                log.info(f"[ROTAÇÃO] Trocando IP — novo session-id: {session_id}")
                processo = abrir_chrome(URL, processo=processo, usar_proxy=usar_proxy, session_id=session_id)

    finally:
        if processo:
            fechar_chrome(processo)

        if CLIENT_AGRO:
            log.info("Fechando conexão CLIENT_AGRO...")
            CLIENT_AGRO.close()
        if CLIENT:
            log.info("Fechando conexão CLIENT...")
            CLIENT.close()


if __name__ == "__main__":
    espera = 1
    while True:
        try:
            main()
            espera = 1
        except Exception as exc:
            log.exception(f"Erro não tratado em main(): {exc}")
            log.info(f"Aguardando {espera} minuto(s) antes de reiniciar...")
            time.sleep(60 * espera)
            espera = min(espera + 1, 10)  # máximo 10 minutos de espera