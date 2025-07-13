import os, re, json, shutil, requests
from bs4 import BeautifulSoup
from pathlib import Path
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
}


def run_parser(base_cat):
    product_links = []
    page = 1
    while True:
        url = base_cat if page == 1 else f"{base_cat}page/{page}/"
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select('a.woocommerce-LoopProduct-link')
        if not items:
            break
        for a in items:
            href = a.get('href')
            if href and href not in product_links:
                product_links.append(href)
        page += 1

    print(f"Найдено товаров в категории: {len(product_links)}")

    data_dir = Path('data/products')
    data_dir.mkdir(parents=True, exist_ok=True)
    dest_root = Path('public/images/products')
    dest_root.mkdir(parents=True, exist_ok=True)

    for link in product_links:
        slug = link.rstrip('/').split('/')[-1]
        print(f"Парсим товар: {slug}")

        resp = requests.get(link, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        title = soup.find('h1', class_='product_title').get_text(strip=True)

        price_amount, discount_amount = '', ''
        price_container = soup.select_one('.price')
        if price_container:
            ins = price_container.find('ins')
            if ins:
                new_amt = ins.find('span', class_='woocommerce-Price-amount')
                if new_amt:
                    discount_amount = re.sub(r"[^\d\s]", "", new_amt.get_text(strip=True))
                old_del = price_container.find('del')
                old_amt = old_del.find('span', class_='woocommerce-Price-amount') if old_del else None
                if old_amt:
                    price_amount = re.sub(r"[^\d\s]", "", old_amt.get_text(strip=True))
            else:
                amt = price_container.find('span', class_='woocommerce-Price-amount')
                if amt:
                    price_amount = re.sub(r"[^\d\s]", "", amt.get_text(strip=True))

        short_desc = (soup.find('h2', class_='elementor-heading-title') or '').get_text(strip=True)

        full_text = ''
        content_inner = soup.select_one('div.content-inner')
        if content_inner:
            blocks = content_inner.select('div.text-content.clearfix.with-meta') or content_inner.select('div.text-content')
            plain = [blk.get_text(separator='\n', strip=True) for blk in blocks]
            full_text = '\n\n'.join(plain)

        product_img_dir = dest_root / slug
        product_img_dir.mkdir(exist_ok=True)

        track = soup.find('div', class_='slick-track')
        anchors = track.select('a.wcgs-slider-image') if track else soup.select('a.wcgs-slider-image')
        img_urls = []
        for a in anchors:
            h = a.get('href')
            if h and h not in img_urls:
                img_urls.append(h)

        def download_image(img_url_idx):
            img_url, idx = img_url_idx
            ext = os.path.splitext(img_url)[1]
            fname = f"{slug}-{idx}{ext}"
            out = product_img_dir / fname
            if not out.exists():
                try:
                    resp = requests.get(img_url, headers=HEADERS, timeout=10)
                    out.write_bytes(resp.content)
                except Exception as e:
                    print(f"Ошибка скачивания {img_url}: {e}")
                    return None
            img_tag = soup.find('a', href=img_url).find('img')
            w = int(img_tag.get('width') or 0)
            h = int(img_tag.get('height') or 0)
            alt = img_tag.get('alt') or ''
            return {'src': f"/images/products/{slug}/{fname}", 'width': w, 'height': h, 'alt': alt}

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = executor.map(download_image, [(url, idx) for idx, url in enumerate(img_urls, start=1)])
            images = [img for img in futures if img]

        product_data = {'slug': slug, 'title': title, 'price': price_amount,
                        'discount': discount_amount, 'shortDescription': short_desc,
                        'description': full_text, 'images': images, 'sourceUrl': link}
        with open(data_dir / f"{slug}.json", 'w', encoding='utf-8') as f:
            json.dump(product_data, f, ensure_ascii=False, indent=2)

        zip_path = dest_root / f"{slug}.zip"
        with ZipFile(zip_path, 'w') as zipf:
            for img_file in product_img_dir.iterdir():
                if img_file.is_file():
                    zipf.write(img_file, arcname=img_file.name)

        shutil.rmtree(product_img_dir)
        print(f"  → {slug}: {len(images)} фото, JSON сохранён, архив {zip_path.name} создан.")

    print("Готово")
