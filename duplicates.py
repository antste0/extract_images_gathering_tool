import os
from PIL import Image
import imagehash

# config

FOLDER = "output"
SIMILARITY_THRESHOLD = 70
DRY_RUN = False  # false - delete right away; true - summarise how many are similar

IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp')

def similarity_percent(hash1, hash2):
    max_bits = len(hash1.hash.flatten())
    distance = hash1 - hash2
    return (1 - distance / max_bits) * 100

def compute_hash(path):
    with Image.open(path) as img:
        w, h = img.size
        resolution = w * h
        img = img.convert("RGB").resize((512, 512), Image.Resampling.LANCZOS)
        img_hash = imagehash.phash(img, hash_size=16)
    return img_hash, resolution

def find_similar(img_hash, hashes, threshold):
    for i, (existing_hash, existing_file, existing_res) in enumerate(hashes):
        similarity = similarity_percent(img_hash, existing_hash)
        if similarity >= threshold:
            return i, existing_file, existing_res, similarity
    return None

def pick_lower_res(path, filename, resolution, folder_path, match):
    _, existing_file, existing_res, similarity = match
    if resolution >= existing_res:
        to_delete = (os.path.join(folder_path, existing_file), existing_file)
        keep = "new"
    else:
        to_delete = (path, filename)
        keep = "existing"
    return to_delete, keep, similarity

def handle_similar(img_hash, filename, resolution, hashes, folder_path, match, dry_run, deleted):
    to_delete, keep, similarity = pick_lower_res(
        os.path.join(folder_path, filename), filename, resolution, folder_path, match
    )
    print(f"SIMILAR ({similarity:.2f}%): {filename} == {match[1]}")

    if keep == "new":
        hashes[match[0]] = (img_hash, filename, resolution)

    if not dry_run:
        os.remove(to_delete[0])
        deleted.append(to_delete[1])
        print(f"DELETED (lower res): {to_delete[1]}")

def remove_similar_images(folder_path, similarity_threshold, dry_run):
    hashes = []
    deleted = []
    similar_count = 0

    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(IMAGE_EXTENSIONS):
            continue

        path = os.path.join(folder_path, filename)

        try:
            img_hash, resolution = compute_hash(path)
            match = find_similar(img_hash, hashes, similarity_threshold)

            if match:
                similar_count += 1
                handle_similar(img_hash, filename, resolution, hashes, folder_path, match, dry_run, deleted)
            else:
                hashes.append((img_hash, filename, resolution))

        except Exception as e:
            print(f"ERROR: {filename} -> {e}")

    return deleted, similar_count

if __name__ == "__main__":
    removed, similar = remove_similar_images(
        FOLDER,
        similarity_threshold=SIMILARITY_THRESHOLD,
        dry_run=DRY_RUN,
    )

    if DRY_RUN:
        print(f"\nDRY RUN: {similar} similar image(s) found, nothing deleted")
    else:
        print("\nDONE:", len(removed), "deleted")
