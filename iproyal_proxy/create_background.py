from dotenv import load_dotenv
import os

load_dotenv()

host = os.getenv("PROXY_HOST")
port = os.getenv("PROXY_PORT")
user = os.getenv("PROXY_USERNAME")
password = os.getenv("PROXY_PASSWORD")

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
    ["blocking"]
);
"""

with open("iproyal_proxy/background.js", "w", encoding="utf-8") as f:
    f.write(background)