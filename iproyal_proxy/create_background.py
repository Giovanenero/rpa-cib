"""
Utilitário standalone para regenerar iproyal_proxy/background.js
com um novo session-id (rotação de IP).

Uso:
    python create_background.py            # gera com session-id aleatório
    python create_background.py [session]  # gera com session-id fornecido
"""
import sys, uuid, re, os
from dotenv import load_dotenv

load_dotenv()

host     = os.getenv("PROXY_HOST", "geo.iproyal.com")
port     = os.getenv("PROXY_PORT", 12321)
user     = os.getenv("PROXY_USERNAME", "")
password = os.getenv("PROXY_PASSWORD", "")

# Aceita session-id como argumento opcional
session_id = sys.argv[1] if len(sys.argv) > 1 else uuid.uuid4().hex[:12]

# Remove session anterior e adiciona nova
password = re.sub(r"_session-[a-f0-9]+", "", password)
password = f"{password}_session-{session_id}"

background = f"""
const config = {{
    mode: "fixed_servers",
    rules: {{
        singleProxy: {{
            scheme: "http",
            host: "{host}",
            port: {port}
        }}
    }}
}};

chrome.proxy.settings.set({{ value: config, scope: "regular" }});

chrome.webRequest.onAuthRequired.addListener(
    () => ({{
        authCredentials: {{
            username: "{user}",
            password: "{password}"
        }}
    }}),
    {{ urls: ["<all_urls>"] }},
    ["asyncBlocking"]
);
"""

out_path = os.path.join(os.path.dirname(__file__), "background.js")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(background)

print(f"background.js gerado — session-id: {session_id}  host: {host}:{port}")