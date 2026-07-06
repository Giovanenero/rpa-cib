import subprocess

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

EXTENSAO = r"C:\Users\SeuUsuario\Desktop\iproyal_proxy"

subprocess.Popen([
    CHROME,
    f"--load-extension={EXTENSAO}",
    "--new-window",
    "https://ipv4.icanhazip.com"
])