import csv
from playwright.sync_api import sync_playwright
from time import sleep

CSV_PATH = "./03 playwright/out.csv"
CSV_FIELDS = ["image_url", "title", "source_url", "description"]
IMG_COUNT = 10
SCROLL_DELAY = 5
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


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://ya.ru/images/search?text=cats", timeout=100000)
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
        sleep(SCROLL_DELAY)
    browser.close()

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(extracted)
print(f"Saved {len(extracted)} rows to {CSV_PATH}")
