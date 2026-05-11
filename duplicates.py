import os
from PIL import Image
import imagehash

def similarity_percent(hash1, hash2):
    """
    Oblicza procent podobieństwa hashy.
    """
    max_bits = len(hash1.hash.flatten())
    distance = hash1 - hash2
    similarity = (1 - distance / max_bits) * 100
    return similarity


def normalize_image(img, size=(512, 512)):
    """
    Ujednolica obraz:
    - ignoruje rozdzielczość,
    - usuwa wpływ proporcji,
    - konwertuje do RGB.
    """
    img = img.convert("RGB")
    img = img.resize(size, Image.Resampling.LANCZOS)
    return img


def remove_similar_images(folder_path, similarity_threshold=95, dry_run=True):
    hashes = []
    deleted = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith((
            '.png', '.jpg', '.jpeg',
            '.bmp', '.gif', '.webp'
        )):
            path = os.path.join(folder_path, filename)

            try:
                with Image.open(path) as img:

                    # ignore resolution
                    img = normalize_image(img)

                    img_hash = imagehash.phash(img, hash_size=16)

                found_similar = False

                for existing_hash, existing_file in hashes:
                    similarity = similarity_percent(
                        img_hash,
                        existing_hash
                    )

                    if similarity >= similarity_threshold:

                        print(
                            f"PODOBNE ({similarity:.2f}%): "
                            f"{filename} == {existing_file}"
                        )

                        found_similar = True

                        if not dry_run:
                            os.remove(path)
                            deleted.append(filename)
                            print(f"USUNIĘTO: {filename}")

                        break

                if not found_similar:
                    hashes.append((img_hash, filename))

            except Exception as e:
                print(f"Błąd: {filename} -> {e}")

    return deleted

# folder to search for duplicates
folder = "output"

removed = remove_similar_images(
    folder,
    similarity_threshold=70,
    dry_run=False
)

print("\n--- PODSUMOWANIE ---")
print(f"Usunięte pliki: {len(removed)}")