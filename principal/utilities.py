import requests
from django.template.loader import render_to_string

DEEPL_API_KEY = "328cdec4-bd45-4ce5-8c6c-6d52c24a0278:fx"

def traducir_html(html_str, idioma_destino='ES'):
    url = "https://api-free.deepl.com/v2/translate"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "auth_key": DEEPL_API_KEY,
        "text": html_str,
        "target_lang": idioma_destino,
        "tag_handling": "html"
    }
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code == 200:
        return response.json()["translations"][0]["text"], idioma_destino
    else:
        error_msg = f"<p>Error: {response.status_code} - {response.text}</p>"
        return error_msg, idioma_destino  # <--- Siempre dos valores
