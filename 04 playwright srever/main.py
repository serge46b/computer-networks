import os
from pathlib import Path

from playwright.sync_api import sync_playwright
from flask import Flask, request, jsonify
import psycopg

from parser import get_img_data


TABLE_NAME = "parsed_images"
IMG_COUNT = 10


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
    with psycopg.connect(os.environ.get("DB_DSN", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_sql)
            conn.commit()


def playwright_parse(url: str = "https://ya.ru/images/search?text=cats"):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=100000)
        array_of_imgs = page.locator("body div.JustifierRowLayout div.SerpItem")
        old_count = 0
        extracted = []
        for i in range(old_count, min(array_of_imgs.count(), old_count + IMG_COUNT)):
            array_of_imgs.nth(i).click()
            print(f"Clicked on image {i} of {array_of_imgs.count()}")
            extracted.append(get_img_data(page))
        old_count = array_of_imgs.count()
        page.locator("body div.extra-content").scroll_into_view_if_needed()
        browser.close()
        return extracted


def insert_img_data(url: str, img: dict):
    with psycopg.connect(os.environ.get("DB_DSN", "")) as conn:
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
    with psycopg.connect(os.environ.get("DB_DSN", "")) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT parse_url, image_url, image_title, source_url, image_description
                FROM {TABLE_NAME}
                """
            )
            rows = cur.fetchall()

    return jsonify(
        [
            {
                "parse_url": row[0],
                "image_url": row[1],
                "image_title": row[2],
                "source_url": row[3],
                "image_description": row[4],
            }
            for row in rows
        ]
    )


if __name__ == "__main__":
    load_env_from_file()
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
