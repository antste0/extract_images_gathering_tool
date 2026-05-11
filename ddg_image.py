import asyncio
import aiohttp
import hashlib
import os
import random
import time
from io import BytesIO
from urllib.parse import urlparse

from PIL import Image
from ddgs import DDGS

# config

QUERIES = [
    # put queries here
]

# max number of images
LIMIT = 3000
OUTPUT_DIR = "output"

MIN_WIDTH = 256
MIN_HEIGHT = 256

CONCURRENCY = 15

BAD_DOMAINS = ["facebook", "fbcdn", "ytimg", "youtube", "tiktok", "twitter", "x.com"]
BAD_KEYWORDS = ["stock", "shutterstock", "getty", "istock", "adobe"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

seen_urls = set()
seen_hashes = set()

headers = {
    "User-Agent": "Mozilla/5.0"
}

# helper functions

def is_bad_domain(url):
    domain = urlparse(url).netloc.lower()
    return any(b in domain for b in BAD_DOMAINS)


def has_bad_keywords(url):
    u = url.lower()
    return any(k in u for k in BAD_KEYWORDS)


def img_hash(data):
    return hashlib.md5(data).hexdigest()


def valid(img):
    return img.width >= MIN_WIDTH and img.height >= MIN_HEIGHT


def safe_ddg_images(ddgs, query, max_retries=3):
    for i in range(max_retries):
        try:
            return list(ddgs.images(query, max_results=100))
        except Exception as e:
            wait = 2 ** i + random.random()
            print(f"[DDG retry {i+1}] {query} -> {e} (sleep {wait:.1f}s)")
            time.sleep(wait)
    return []

# async

async def fetch_image(session, sem, url, saved_counter):
    async with sem:

        if saved_counter[0] >= LIMIT:
            return

        if is_bad_domain(url) or has_bad_keywords(url):
            return

        try:
            async with session.get(url, timeout=15) as resp:

                if resp.status in (403, 404, 429):
                    return

                if "image" not in resp.headers.get("Content-Type", ""):
                    return

                data = await resp.read()

                h = img_hash(data)
                if h in seen_hashes:
                    return

                try:
                    img = Image.open(BytesIO(data))
                except Exception:
                    return

                if not valid(img):
                    return

                seen_hashes.add(h)

                path = os.path.join(OUTPUT_DIR, f"img_{saved_counter[0]}.jpg")
                img.convert("RGB").save(path, "JPEG", quality=95)

                saved_counter[0] += 1
                print(f"[{saved_counter[0]}] OK {url}")

        except Exception:
            return


async def main():

    print("SEARCH...")

    all_results = []

    with DDGS() as ddgs:
        for q in QUERIES:
            print("query:", q)

            batch = safe_ddg_images(ddgs, q)

            if not batch:
                print(f"[WARN] empty results: {q}")
                continue

            all_results.extend(batch)

    # dedupe URLs
    urls = []

    for r in all_results:
        url = r.get("image")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        urls.append(url)

    print("TOTAL UNIQUE URLS:", len(urls))

    sem = asyncio.Semaphore(CONCURRENCY)
    saved_counter = [0]

    async with aiohttp.ClientSession(headers=headers) as session:

        tasks = [
            fetch_image(session, sem, url, saved_counter)
            for url in urls
        ]

        await asyncio.gather(*tasks)

    print("\nDONE:", saved_counter[0])

if __name__ == "__main__":
    asyncio.run(main())