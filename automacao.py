import pyautogui, subprocess, PyPDF2, tempfile
import time, os, random, re, io, base64
from tenacity import retry, stop_after_attempt, wait_fixed
from pathlib import Path
from pymongo import MongoClient
import pyperclip
from dotenv import load_dotenv

load_dotenv()


url = os.getenv("URL_SITE")
FOLDER_PATH = 'imgs'
PERFIL = tempfile.mkdtemp()

DOWNLOADS = Path.home() / "Downloads"
MONGO_URI = os.getenv("URI_WISE")
CLIENT = MongoClient(MONGO_URI)
DATABASE = CLIENT["RECEITA_FEDERAL"]
COLLECTION = DATABASE["CAFIR"]

@retry(stop=stop_after_attempt(10), wait=wait_fixed(0.5),     retry_error_callback=lambda retry_state: None)
def localizar_imagem(imagem, confidence=0.9, grayscale=False):
    return pyautogui.locateCenterOnScreen(
        imagem,
        confidence=confidence,
        grayscale=grayscale,
    )


def esperar_download(download_dir, timeout=60) -> str | None:
    inicio = time.time()
    while time.time() - inicio < timeout:
        if os.path.exists(download_dir) and not download_dir.endswith('.crdownload'):
            return True

    return False


def digitar_humanizado(texto: str, intervalo_min: float = 0.04, intervalo_max: float = 0.15):
    for caractere in texto:
        pyautogui.write(caractere, interval=random.uniform(intervalo_min, intervalo_max))


def acessar_site(url: str, processo=None):
    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    # fecha o processo
    if processo and processo.poll() is None:
        processo.terminate()
        processo.wait()

    # abre um processo novo
    processo = subprocess.Popen([
        chrome,
        f"--user-data-dir={PERFIL}",
        "--start-maximized",
        "--no-first-run",
        "--no-default-browser-check",
        url
    ])

    time.sleep(2)

    aceitar_cookies()

    return processo


def aceitar_cookies():
    time.sleep(random.uniform(1.5, 2.8))
    
    position = localizar_imagem(os.path.join(FOLDER_PATH, '1-aceitar_cookies.png'), confidence=0.9)

    if position is None:
        print("Botão de aceitar cookies não encontrado.")
        return False

    # Pequena variação no ponto de clique
    x = position.x + random.randint(-8, 8)
    y = position.y + random.randint(-4, 4)

    # Movimento com duração variável
    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))

    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.click()
    time.sleep(random.uniform(0.3, 0.8))

    return True


def pesquisar_cib(cib: str):

    position = localizar_imagem(os.path.join(FOLDER_PATH, '2-informa_cib.png'), confidence=0.8)
    if not position:
        print("Campo de pesquisa CIB não encontrado.")
        return False
    
    x = position.x + random.randint(-8, 8)
    y = position.y + random.randint(-4, 4)

    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))

    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.click()
    time.sleep(random.uniform(0.3, 0.8))

    digitar_humanizado(cib)

    position = localizar_imagem(os.path.join(FOLDER_PATH, '3-emitir_certidao.png'), confidence=0.8)
    if not position:
        print("Botão de emitir certidão não encontrado.")
        return False
    
    x = position.x + random.randint(-8, 8)
    y = position.y + random.randint(-4, 4)

    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))

    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.click()
    time.sleep(random.uniform(0.3, 0.8))


def fazer_nova_consulta():
    # fazer nova consulta
    pyautogui.press("end")
    time.sleep(0.5)

    position = localizar_imagem(os.path.join(FOLDER_PATH, '10-nova_consulta.png'), confidence=0.8)
    if not position:
        print("Botão de nova consulta não encontrado.")
        return False
    
    x = position.x + random.randint(-8, 8)
    y = position.y + random.randint(-4, 4)
    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))
    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.click()
    time.sleep(random.uniform(0.3, 0.8))

    return True


def verificar_certidao_valida_encontrada(cib: str) -> str | None:

    position = localizar_imagem(os.path.join(FOLDER_PATH, '4-certidao_valida_encontrada.png'), confidence=0.8)
    if not position:
        print("Certidão válida não encontrada.")    
        return None
    
    position = localizar_imagem(os.path.join(FOLDER_PATH, '5-consultar_certidao.png'), confidence=0.8)
    if not position:
        print("Botão de consultar certidão não encontrado.")
        return False

    x = position.x + random.randint(-8, 8) - position.x / 4
    y = position.y + random.randint(-4, 4)

    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))
    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.click()
    time.sleep(random.uniform(0.3, 0.8))

    # espera carregar
    time.sleep(random.uniform(1.5, 2.8))
    pyautogui.scroll(-200)
    time.sleep(0.5)

    # filtra pela data de validade
    position = localizar_imagem(os.path.join(FOLDER_PATH, '6-data_validade.png'), confidence=0.8)
    if not position:
        print("Filtro de data de validade não encontrado.")
        return False
    
    x = position.x + random.randint(-8, 8)
    y = position.y + random.randint(-4, 4)
    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))
    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.click()
    time.sleep(random.uniform(0.3, 0.8))
    pyautogui.scroll(-200)
    time.sleep(0.5)

    # consultar certidão valida
    position = localizar_imagem(os.path.join(FOLDER_PATH, '7-consultar_certidao.png'), confidence=0.8)
    if not position:
        print("Botão de consultar certidão não encontrado.")
        return False
    
    x = position.x + random.randint(-8, 8)
    y = position.y + random.randint(-4, 4)
    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))
    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.click()
    time.sleep(random.uniform(0.3, 0.8))
    pyautogui.scroll(-200)
    time.sleep(0.5)

    resultados = list(pyautogui.locateAllOnScreen(os.path.join(FOLDER_PATH, '8-baixar_2_via.png'), confidence=0.9))
    if not resultados:
        print("Botão de baixar 2ª via não encontrado.")
        return False
    
    position = resultados[0]
    position = pyautogui.center(position)
    x = position.x + random.randint(-4, 4)
    y = position.y + random.randint(-4, 4)
    pyautogui.moveTo(x, y, duration=random.uniform(0.3, 0.8))
    time.sleep(random.uniform(0.1, 0.4))
    pyautogui.click()
    time.sleep(random.uniform(0.3, 0.8))

    pyautogui.scroll(500)
    time.sleep(0.5)

    return True


def get_line(lines: list[str], name: str):

    for line in lines:
        if name in line.lower():
            return line

    return None


def parse_pdf(file_path: str, cib: str) -> dict | None:

    try:

        with open(file_path, "rb") as f:
            content = f.read()

        pdf = PyPDF2.PdfReader(io.BytesIO(content))

        lines = pdf.pages[0].extract_text().split("\n")

        lines = [l.replace("\xa0", " ").strip() for l in lines]

        data = {
            "CIB": cib,
            "PDF": base64.b64encode(content).decode(),
        }

        line = get_line(lines, "nome do imóvel")
        if line:
            data["NM_IMOVEL"] = line.split(":")[1].strip()

        line = get_line(lines, "município")
        if line:
            data["NM_MUNICIPIO"] = line.split(":")[1].strip()
            data["UF"] = line.split(":")[2].strip()

        #line = get_line(lines, "cpf")
        #if line:
        #    data["CPF_CNPJ"] = re.sub(r"\D", "", line)

        line = get_line(lines, 'área total (em hectares):')
        if line:
            data['AREA_TOTAL'] = float(re.sub(r'[^0-9,]', '', line).replace(',', '.'))

        line = get_line(lines, 'contribuinte:')
        if line:
            data['NM_CONTRIBUINTE'] = line.split(":")[1].strip()

        line = get_line(lines, 'cpf:')
        if line:
            data['IN_CPF'] = True
            data['CPF_CNPJ'] = re.sub(r'\D', '', line)  
        else:
            line = get_line(lines, 'cnpj:')
            if line:
                data['IN_CPF'] = False
                data['CPF_CNPJ'] = re.sub(r'\D', '', line) 

        line = get_line(lines, 'emitida às ')
        if line:
            data['DT_EMISSAO'] = line.replace('Emitida às ', '').replace('<hora e data de Brasília>.', '').replace(' do dia ', ' ').strip()

        line = get_line(lines, 'válida até ')
        if line:
            data['DT_VALIDADE'] = line.replace('Válida até ', '').strip()[:-1]

        line = get_line(lines, 'código de controle da certidão: ')
        if line:
            data['CODIGO_CERTIDAO'] = line.replace('Código de controle da certidão:', '').strip()

        return data

    except Exception as e:
        print(f"Erro ao extrair dados do PDF: {e}")

        return None

    finally:

        if os.path.exists(file_path):
            os.remove(file_path)


def capturar_erro() -> str | None:
    pyautogui.hotkey("ctrl", "a")
    time.sleep(random.uniform(0.3, 0.8))
    pyautogui.hotkey("ctrl", "c")
    time.sleep(random.uniform(0.3, 0.8))
    texto = pyperclip.paste()
    lines = [line.strip() for line in texto.split('\n') if line.strip()]
    index = next(index for index, line in enumerate(lines) if line.lower().startswith("avaliar serviço"))
    lines = lines[10:index]
    texto = "\n".join(lines)

    pyautogui.press("end")
    time.sleep(0.5)

    largura, altura = pyautogui.size()

    pyautogui.moveTo(largura / 2, altura - 200, duration=random.uniform(0.3, 0.8))
    pyautogui.click()
    return texto


def extract_cib(cib: str, chrome=None, fechar_chrome=True) -> tuple[dict, str]:
    
    data, texto = None, None
    if not chrome:
        chrome = acessar_site(url)

    pesquisar_cib(cib)
    baixou = verificar_certidao_valida_encontrada(cib)

    file_path = os.path.join(DOWNLOADS, f"Certidao-{cib}.pdf")

    if baixou or baixou is None:
        # verifica se baixou(1 emissão)
        if esperar_download(file_path, timeout=2):
            data = parse_pdf(file_path, cib)

    if not data:
        texto = capturar_erro()
    
    if fechar_chrome:
        chrome.terminate()   # Fecha o processo
        chrome.wait() 

    return data, texto


def main(): 

    CLIENT_AGRO = MongoClient(os.getenv("URI_AGRO"))
    DATABASE_AGRO = CLIENT_AGRO["AGRONEGOCIO"]
    COLLECTION_AGRO = DATABASE_AGRO["CAFIR_ld"]
    COLLECTION_AGRO_PDF = DATABASE_AGRO["CAFIR_PDF_ld"]
    COLLECTION_AGRO_ERROR = DATABASE_AGRO["CAFIR_ERROR_ld"]

    doc = COLLECTION_AGRO.find_one(
        {"CIB": {"$ne": None}},
        {"_id": 0, "CIB": 1},
        sort=[("CIB", -1)]
    )

    cib = doc['CIB'] if doc else None
    
    filter = {'SG_UF': 'SC', 'NR_IMOVEL': {'$ne': None, '$gt': cib}} if cib else {'SG_UF': 'SC', 'NR_IMOVEL': {'$ne': None}}
    docs = COLLECTION.find(filter, {'_id': 0, 'NR_IMOVEL': 1, 'SG_UF': 1}).sort([('SG_UF', 1), ('NR_IMOVEL', 1)])    
    cibs = [doc['NR_IMOVEL'] for doc in docs]
    
    processo = acessar_site(url, processo=None)

    datas = []
    datas_pdf = []
    datas_error = []

    for index, cib in enumerate(cibs):
    
        data, texto = extract_cib(
            cib, 
            chrome=processo, 
            fechar_chrome=False
        )

        if not data:
            datas_error.append({'CIB': cib, 'ERRO': texto})
        
        else:
            datas_pdf.append({'CPF_CNPJ': data['CPF_CNPJ'], 'PDF': data['PDF']})
            datas.append({k: v for k, v in data.items() if k != 'PDF'})

        if (index + 1)%10 == 0 or not fazer_nova_consulta():
            processo = acessar_site(url, processo=processo)
            
            if datas:
                COLLECTION_AGRO.insert_many(datas)
            
            if datas_pdf:
                COLLECTION_AGRO_PDF.insert_many(datas_pdf)

            if datas_error:
                COLLECTION_AGRO_ERROR.insert_many(datas_error)

            

    

if __name__ == "__main__":
    main()