import io
import os

import fitz  # pip install pymupdf
from PIL import Image


# config

PDF_PATH = "pdf/RD2026_PL.pdf"
OUTPUT_DIR = "output"

# minimum image dimensions
MIN_WIDTH = 100
MIN_HEIGHT = 100

# page range (starting from 1)
START_PAGE = 157
END_PAGE = 175



def save_images_from_pdf(
    pdf_path,
    output_dir,
    min_width,
    min_height,
    start_page,
    end_page
):
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)

    total_pages = len(doc)

    # clamp page range
    start_page = max(1, start_page)
    end_page = min(total_pages, end_page)

    saved = 0
    skipped = 0

    print(f"PDF ma {total_pages} stron")
    print(f"Przetwarzanie stron: {start_page} -> {end_page}")

    # range() starts indexing from 0
    for page_index in range(start_page - 1, end_page):

        page = doc[page_index]

        image_list = page.get_images(full=True)

        print(
            f"\nStrona {page_index + 1}: "
            f"znaleziono {len(image_list)} obrazów"
        )

        for img_index, img in enumerate(image_list):

            xref = img[0]

            try:
                base_image = doc.extract_image(xref)

                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                image = Image.open(io.BytesIO(image_bytes))

                width, height = image.size

                # filter by dimensions
                if width >= min_width and height >= min_height:

                    filename = (
                        f"page_{page_index + 1}_"
                        f"img_{img_index + 1}_"
                        f"{width}x{height}.{image_ext}"
                    )

                    output_path = os.path.join(
                        output_dir,
                        filename
                    )

                    with open(output_path, "wb") as f:
                        f.write(image_bytes)

                    print(f"  ZAPISANO: {filename}")

                    saved += 1

                else:
                    print(
                        f"  POMINIĘTO: "
                        f"{width}x{height} "
                        f"(minimum {min_width}x{min_height})"
                    )

                    skipped += 1

            except Exception as e:
                print(f"  BŁĄD: {e}")

    print("\n===== PODSUMOWANIE =====")
    print(f"Zapisane: {saved}")
    print(f"Pominięte: {skipped}")


if __name__ == "__main__":

    save_images_from_pdf(
        PDF_PATH,
        OUTPUT_DIR,
        MIN_WIDTH,
        MIN_HEIGHT,
        START_PAGE,
        END_PAGE
    )