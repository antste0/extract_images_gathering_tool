import asyncio
import hashlib
import os
import random
import time
from io import BytesIO
from urllib.parse import urlparse

import aiohttp
from ddgs import DDGS
from PIL import Image

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
QUERY_CONCURRENCY = 5  # max concurrent DDG queries

os.makedirs(OUTPUT_DIR, exist_ok=True)

seen_urls = set()
seen_hashes = set()

headers = {
    "User-Agent": "Mozilla/5.0"
}

# helper functions

BAD_DOMAINS = ["facebook", "fbcdn", "ytimg", "youtube", "tiktok", "twitter", "x.com"]

def is_bad_domain(url):
    domain = urlparse(url).netloc.lower()
    return any(b in domain for b in BAD_DOMAINS)

BAD_KEYWORDS = ["stock", "shutterstock", "getty", "istock", "adobe"]

def has_bad_keywords(url):
    u = url.lower()
    return any(k in u for k in BAD_KEYWORDS)

def img_hash(data):
    return hashlib.md5(data).hexdigest()

def valid(img):
    return img.width >= MIN_WIDTH and img.height >= MIN_HEIGHT

def safe_ddg_images(query, max_retries=3):
    # synchronous function meant to be called in a separate thread
    for i in range(max_retries):
        try:
            with DDGS() as ddgs:
                return list(ddgs.images(query, max_results=100))
        except Exception as e:
            wait = 2 ** i + random.random()
            print(f"[DDG retry {i+1}] {query} -> {e} (sleep {wait:.1f}s)")
            time.sleep(wait)
    return []

# async

async def fetch_query(sem_query, query):
    # run DDG search in a thread pool, bounded by QUERY_CONCURRENCY
    async with sem_query:
        print("query:", query)
        batch = await asyncio.to_thread(safe_ddg_images, query)
        if not batch:
            print(f"[WARN] empty results: {query}")
        return batch

def should_skip_url(url):
    return is_bad_domain(url) or has_bad_keywords(url)

def try_open_image(data):
    try:
        return Image.open(BytesIO(data))
    except Exception:
        return None

def save_image(img, data, saved_counter):
    seen_hashes.add(img_hash(data))
    path = os.path.join(OUTPUT_DIR, f"img_{saved_counter[0]}.jpg")
    img.convert("RGB").save(path, "JPEG", quality=95)
    saved_counter[0] += 1
    print(f"[{saved_counter[0]}] OK")

async def fetch_and_save(session, url, saved_counter):
    try:
        async with session.get(url, timeout=15) as resp:
            if resp.status in (403, 404, 429):
                return
            if "image" not in resp.headers.get("Content-Type", ""):
                return
            data = await resp.read()
            if img_hash(data) in seen_hashes:
                return
            img = try_open_image(data)
            if img is None or not valid(img):
                return
            save_image(img, data, saved_counter)
    except Exception:
        return

async def fetch_image(session, sem, url, saved_counter):
    async with sem:
        if saved_counter[0] >= LIMIT:
            return
        if should_skip_url(url):
            return
        await fetch_and_save(session, url, saved_counter)

def collect_urls(results_per_query):
    urls = []
    for batch in results_per_query:
        for r in batch:
            url = r.get("image")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            urls.append(url)
    return urls

async def run_queries():
    sem_query = asyncio.Semaphore(QUERY_CONCURRENCY)
    tasks = [fetch_query(sem_query, q) for q in QUERIES]
    return await asyncio.gather(*tasks)

async def download_images(urls):
    sem = asyncio.Semaphore(CONCURRENCY)
    saved_counter = [0]
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [fetch_image(session, sem, url, saved_counter) for url in urls]
        await asyncio.gather(*tasks)
    return saved_counter[0]

async def main():
    print("SEARCH...")
    results_per_query = await run_queries()
    urls = collect_urls(results_per_query)
    print("TOTAL UNIQUE URLS:", len(urls))
    saved = await download_images(urls)
    print("\nDONE:", saved)

if __name__ == "__main__":
    asyncio.run(main())