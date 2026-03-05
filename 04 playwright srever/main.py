from playwright.sync_api import sync_playwright
from flask import Flask, request, jsonify
import psycopg

import os
from time import sleep
from pathlib import Path


app = Flask(__name__)


def load_env_from_file(filename: str = ".env") -> None:
    env_path = Path(__file__).with_name(filename)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_from_file()

DB_DSN: str = os.environ.get("DB_DSN", "")
if not DB_DSN:
    raise RuntimeError("DB_DSN is not set. Add it to .env or environment variables.")

TABLE_NAME = "parsed_images"
IMG_COUNT = 10
SCROLL_CNT = 3


def get_img_data(page):
    data_container = page.wait_for_selector("body div.ImagesViewer-LayoutContainer")
    if data_container is None:
        raise RuntimeError("Image popup not found")
    image_el = data_container.query_selector("div.ImagesViewer-Wrapper img")
    data_el = data_container.query_selector("div.MMOrganicSnippet")
    if image_el is None or data_el is None:
        raise RuntimeError("Image not found or data not found")
    image_url = image_el.get_attribute("src")
    if image_url:
        image_url = "https:" + image_url
    img_title_el = data_el.query_selector("div.MMOrganicSnippet-TitleWrap a")
    img_src_el = data_el.query_selector("div.MMOrganicSnippet-Subtitle a")
    img_description_el = data_el.query_selector("div.MMOrganicSnippet-Description")
    if img_title_el is None or img_src_el is None or img_description_el is None:
        raise RuntimeError("One of data elements is missing")
    img_title = img_title_el.inner_text()
    img_src = img_src_el.get_attribute("href")
    img_description = img_description_el.inner_html()
    page.locator("body button.ImagesViewer-Close").click()
    return {
        "image_url": image_url or "",
        "title": img_title,
        "source_url": img_src or "",
        "description": img_description,
    }


def init_db():
    """Create the table if it does not exist."""
    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id SERIAL PRIMARY KEY,
            parse_url TEXT,
            image_url TEXT,
            image_title TEXT,
            source_url TEXT,
            image_description TEXT
        )
    """
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
            conn.commit()


def playwright_parse(url: str = "https://ya.ru/images/search?text=cats"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, timeout=100000)
        array_of_imgs = page.locator("body div.JustifierRowLayout div.SerpItem")
        old_cnt = 0
        extracted = []
        for _ in range(SCROLL_CNT):
            for i in range(old_cnt, min(array_of_imgs.count(), old_cnt + IMG_COUNT)):
                img_el = array_of_imgs.nth(i)
                img_el.click()
                print(f"Clicked on image {i} of {array_of_imgs.count()}")
                extracted.append(get_img_data(page))
            old_cnt = array_of_imgs.count()
            page.locator("body div.extra-content").scroll_into_view_if_needed()
        browser.close()
        return extracted


def insert_img_data(url: str, img: dict):
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {TABLE_NAME}
                    (parse_url, image_url, image_title, source_url, image_description)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    url,
                    img.get("image_url") or "",
                    img.get("title") or "",
                    img.get("source_url") or "",
                    img.get("description") or "",
                ),
            )
            conn.commit()


@app.route("/parse")
def parse():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "Missing 'url' query parameter"}), 400

    print(f"Received URL to parse: {url}")
    extracted = playwright_parse(url)
    for img in extracted:
        insert_img_data(url, img)
    return jsonify({"parsed_url": url})


@app.route("/get")
def get_data():
    init_db()
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT parse_url, image_url, image_title, source_url, image_description
                FROM {TABLE_NAME}
                """
            )
            rows = cur.fetchall()

    result = [
        {
            "parse_url": r[0],
            "image_url": r[1],
            "image_title": r[2],
            "source_url": r[3],
            "image_description": r[4],
        }
        for r in rows
    ]
    return jsonify(result)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
