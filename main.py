import os
import re
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))

SPROUT_URL = "https://sprout.link/bloomberglinea"
MAX_ARTICLES = 15
MODEL = "openai/gpt-oss-120b"
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "resumenes"))
MAX_CONTENT_CHARS = 2000  # ~500 tokens; límite del modelo: 8000 TPM


def _extract_article_urls(raw_content: str) -> list[str]:
    """Extrae los destinos de los tiles de imagen del markdown de sprout.link.
    Devuelve bloomberglinea.com y bit.ly (que Tavily resolverá al extraer).
    Excluye links de perfil (instagram, sprout assets)."""
    # Patrón: [![...](sproutsocial_img)](destination_url)
    destinations = re.findall(
        r'\[!\[.*?\]\(https://network-media\.sproutsocial\.com/[^)]+\)\]\(([^)]+)\)',
        raw_content,
    )
    seen, unique = set(), []
    for url in destinations:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def fetch_news() -> list[dict]:
    """Obtiene los primeros 15 links de sprout.link/bloomberglinea y extrae su contenido."""
    client = TavilyClient(api_key=TAVILY_API_KEY)

    print(f"[{datetime.now():%H:%M:%S}] Obteniendo links desde {SPROUT_URL}...")
    # Añadir timestamp para evitar caché de Tavily
    cache_bust_url = f"{SPROUT_URL}?_={int(datetime.now().timestamp())}"
    result = client.extract(urls=[cache_bust_url], extract_depth="advanced")

    raw_content = result["results"][0].get("raw_content", "") if result.get("results") else ""
    candidate_urls = _extract_article_urls(raw_content)[:MAX_ARTICLES + 5]  # pedir extra para compensar posibles no-bloomberglinea

    if not candidate_urls:
        print("No se encontraron links en la página.")
        return []

    print(f"[{datetime.now():%H:%M:%S}] {len(candidate_urls)} links encontrados. Extrayendo contenido...")

    articles = []
    seen_urls = set()
    article_num = 1
    for url in candidate_urls:
        if len(articles) >= MAX_ARTICLES:
            break
        try:
            res = client.extract(urls=[url])
            if not res or not res.get("results"):
                continue
            item = res["results"][0]
            final_url = item.get("url") or url
            parsed = urlparse(final_url)
            clean_url = urlunparse(parsed._replace(query=""))
            # Aceptar bloomberglinea.com y bit.ly (redirige a Bloomberg Línea)
            if "bloomberglinea.com" not in clean_url and "bit.ly" not in clean_url:
                continue
            if clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)
            contenido = item.get("raw_content") or item.get("content", "")
            titulo = item.get("title") or f"Noticia {article_num}"
            if not contenido:
                continue
            articles.append({"id": article_num, "titulo": titulo, "url": clean_url, "contenido": contenido})
            print(f"  [{article_num}/{MAX_ARTICLES}] {titulo[:70]}")
            article_num += 1
        except Exception as e:
            print(f"  Error al extraer {url}: {e}")

    print(f"[{datetime.now():%H:%M:%S}] Total: {len(articles)} artículos obtenidos.\n")
    return articles


def summarize_article(client: Groq, article: dict) -> str:
    """Genera un resumen de una noticia usando Groq."""
    contenido = article["contenido"][:MAX_CONTENT_CHARS]
    prompt = (
        "Eres un periodista profesional. Resume la siguiente noticia en español "
        "en 3-4 oraciones claras y concisas, destacando los puntos más importantes.\n\n"
        f"NOTICIA:\n{contenido}\n\nRESUMEN:"
    )

    stream = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        max_completion_tokens=512,
        top_p=1,
        reasoning_effort="medium",
        stream=True,
        stop=None,
    )

    result = ""
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            result += delta
    return result.strip()


def send_email(resultados: list[dict], fecha: str) -> None:
    """Envía los resúmenes por correo electrónico en formato HTML."""
    if not all([EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO]):
        print("Advertencia: credenciales de email incompletas en .env, omitiendo envío.")
        return

    items_html = ""
    for r in resultados:
        items_html += f"""
        <div style="margin-bottom:24px; border-left:3px solid #cce0ff; padding-left:12px;">
            <p style="margin:0 0 4px 0; font-weight:bold; font-size:14px;">{r['titulo']}</p>
            <p style="margin:0 0 8px 0; color:#333;">{r['resumen']}</p>
            <a href="{r['url']}" style="color:#0066cc; font-size:13px;">Leer noticia completa →</a>
        </div>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif; max-width:700px; margin:auto; color:#222;">
        <h2 style="border-bottom:2px solid #0066cc; padding-bottom:8px;">
            Noticias Bloomberg Línea — {fecha}
        </h2>
        {items_html}
        <p style="color:#999; font-size:12px; margin-top:32px;">
            Generado automáticamente con Groq ({MODEL})
        </p>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Resumen Bloomberg Línea — {fecha}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html, "html", "utf-8"))

    print(f"[{datetime.now():%H:%M:%S}] Enviando email a {EMAIL_TO}...")
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    print(f"[{datetime.now():%H:%M:%S}] Email enviado correctamente.")


def run():
    """Flujo principal: obtener noticias, generar resúmenes y enviar email."""
    if not GROQ_API_KEY or not TAVILY_API_KEY:
        raise ValueError("Faltan GROQ_API_KEY o TAVILY_API_KEY en el archivo .env")

    OUTPUT_DIR.mkdir(exist_ok=True)
    fecha = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"resumen_{fecha}.json"

    articles = fetch_news()
    if not articles:
        print("No se encontraron noticias.")
        return

    groq_client = Groq(api_key=GROQ_API_KEY)
    resultados = []

    for article in articles:
        print(f"[{datetime.now():%H:%M:%S}] Resumiendo {article['id']}/{len(articles)}: {article['titulo'][:50]}...")
        try:
            resumen = summarize_article(groq_client, article)
            resultados.append({
                "id": article["id"],
                "fecha": fecha,
                "titulo": article["titulo"],
                "url": article["url"],
                "resumen": resumen,
            })
        except Exception as e:
            print(f"  Error en noticia {article['id']}: {e}")
            resultados.append({
                "id": article["id"],
                "fecha": fecha,
                "titulo": article["titulo"],
                "url": article["url"],
                "resumen": f"Error al generar resumen: {e}",
            })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"\n[{datetime.now():%H:%M:%S}] Resúmenes guardados en: {output_file}")
    print(f"Total procesadas: {len(resultados)} noticias.\n")

    print("=" * 60)
    print(f"NOTICIAS DEL DÍA - {fecha}")
    print("=" * 60)
    for r in resultados:
        print(f"\n[{r['id']}] {r['titulo']}")
        print(f"    {r['resumen']}")
        print(f"    Fuente: {r['url']}")
        print("-" * 40)

    send_email(resultados, fecha)


if __name__ == "__main__":
    run()
