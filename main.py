import os
import json
import hashlib
from datetime import datetime
from html_to_markdown import convert_to_markdown

from utils import clean_html, fetch_articles, save_md
from vector_store_uploader import VectorStoreUploader

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ARTICLE_DIR = os.path.join(OUTPUT_DIR, "articles")
META_FILE = os.path.join(OUTPUT_DIR, "article_meta.json")
LOG_FILE = os.path.join(OUTPUT_DIR, "job_log.txt")
os.makedirs(ARTICLE_DIR, exist_ok=True)

API_URL = "https://support.optisigns.com/api/v2/help_center/en-us/articles?page=12&per_page=30.json"

if os.path.exists(META_FILE):
    with open(META_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)
else:
    meta = {}

delta_files = []
log_lines = []
added = updated = skipped = 0

articles = fetch_articles(API_URL)
print(f"[INFO] - Fetched {len(articles)} articles")

for art in articles:
    title = art["title"]
    html_url = art["html_url"]

    slug = str(art["id"])
    last_modified = art.get("updated_at", "")

    html = clean_html(art["body"])
    body_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()

    status = ""
    if slug not in meta.keys():
        status = "added"
        added += 1
    elif meta[slug]["hash"] != body_hash:
        status = "updated"
        updated += 1
    else:
        status = "skipped"
        skipped += 1

    if status in ("added", "updated"):
        markdown = convert_to_markdown(html, heading_style="atx")
        title_slug = save_md(ARTICLE_DIR, title, html_url, markdown)
        delta_files.append(os.path.join(ARTICLE_DIR, f"{title_slug}.md"))

    meta[slug] = {
        "hash": body_hash,
        "last_modified": last_modified,
        "html_url": html_url,
        "title": title,
    }
    log_lines.append(f"[{status.upper()}] {title} ({html_url})")

with open(META_FILE, "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
log_header = f"=== Job Run: {now} ===\n"
log_summary = f"\nSummary: added={added}, updated={updated}, skipped={skipped}\n"
log_content = "\n".join(log_lines)
with open(LOG_FILE, "a", encoding="utf-8") as f:
    f.write(log_header + log_summary + log_content + "\n\n")

print(log_summary)
print(f"[INFO] - See full log at: {os.path.abspath(LOG_FILE)}\n\n")

store_name = "OptiSigns Bot"
uploader = VectorStoreUploader(api_key=os.getenv("OPENAI_API_KEY"))

vector_stores = uploader.list_vector_stores()
existing = next((vs for vs in vector_stores if vs["name"] == store_name), None)

if existing:
    vector_store_id = existing["id"]
else:
    vector_store = uploader.create_vector_store(store_name)
    vector_store_id = vector_store.get("id")
    print(
        f"[INFO] - Vector store ID not found. Create a new vector store with id: {vector_store_id}."
    )

if delta_files:
    print(f"[INFO] - Found {len(delta_files)} delta files to upload.")
    stats = uploader.upload_files_to_vector_store(delta_files, vector_store_id)
else:
    print("[INFO] - No new or updated files to upload.")
    vs = uploader.retrive_vector_store(vector_store_id)
