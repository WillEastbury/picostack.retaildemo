"""
Generate WaveStore product and marketing images using gpt-image-1 via Azure OpenAI.
Images are saved to src/wavestore_frontend/static/images/
"""
import os
import base64
import time
from pathlib import Path
from openai import AzureOpenAI

ENDPOINT = os.environ["AZURE_OPENAI_IMAGE_ENDPOINT"]
KEY = os.environ["AZURE_OPENAI_IMAGE_KEY"]
DEPLOYMENT = "gpt-image-1"
OUT_DIR = Path(__file__).parent.parent / "src" / "wavestore_frontend" / "static" / "images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

client = AzureOpenAI(
    api_key=KEY,
    azure_endpoint=ENDPOINT,
    api_version="2025-04-01-preview",
)

# Images to generate: (filename, prompt)
IMAGES = [
    # --- Product category images ---
    (
        "product-jacket.jpg",
        "Professional product photography of a waterproof outdoor shell jacket in slate blue and burnt orange, "
        "hanging against a clean white background with soft studio lighting, commercial retail style, "
        "sharp focus, high resolution, no text",
    ),
    (
        "product-boots.jpg",
        "Professional product photography of rugged leather hiking boots in dark brown on a white background, "
        "studio lighting, retail product shot, sharp focus, top angle showing tread, no text",
    ),
    (
        "product-coffee.jpg",
        "Professional product photography of a premium matte black coffee tin and matching pack on a white background, "
        "soft studio lighting, warm coffee brown accents, retail style, no text",
    ),
    (
        "product-kitchen-box.jpg",
        "Professional product photography of a set of stackable kitchen storage containers in matte white with "
        "clean lines, white background, soft studio lighting, modern minimalist retail style, no text",
    ),
    (
        "product-headphones.jpg",
        "Professional product photography of sleek over-ear wireless headphones in matte black and silver, "
        "floating on white background, dramatic studio lighting, consumer electronics retail style, no text",
    ),
    (
        "product-aurora-jacket.jpg",
        "Professional product photography of a premium packable waterproof hiking jacket in deep purple with "
        "orange zip details, hood folded down, white background, studio lighting, outdoor retail style, no text",
    ),
    (
        "product-cold-brew.jpg",
        "Professional product photography of three sleek cold brew coffee cans in matte black with subtle wave "
        "graphics, on white background, soft cool lighting, artisan beverage retail style, no text",
    ),
    # --- WaveStore hero / brand image ---
    (
        "wavestore-hero.jpg",
        "A vibrant retail hero banner image for an online shop called WaveStore. Deep purple gradient background "
        "fading to warm orange on the right. Minimal geometric wave pattern in the background. "
        "A glowing stylised wave-shaped logo mark in the centre. Modern, clean, premium feel. "
        "No text, pure graphic design, wide landscape 16:9 aspect ratio",
    ),
    # --- Offer / promo banners ---
    (
        "banner-summer-sale.jpg",
        "Wide retail promotional banner for a summer sale. Bold deep purple to warm orange gradient background. "
        "Large percentage discount badge shape in bright orange. Scattered product silhouettes (jacket, boots, "
        "headphones) floating artistically. Modern graphic design style, no text, landscape orientation",
    ),
    (
        "banner-new-arrivals.jpg",
        "Wide retail promotional banner for new arrivals season. Clean dark navy to rich purple gradient. "
        "Stylised product cards floating at angles showing outdoor clothing and electronics silhouettes. "
        "Star burst and sparkle accent shapes in orange and gold. No text, wide landscape format",
    ),
    (
        "banner-free-delivery.jpg",
        "Wide retail promotional banner about delivery offer. Deep midnight purple background with subtle "
        "circuit-like wave pattern. A glowing delivery van silhouette in bright orange. "
        "Speed lines and package silhouettes. Modern clean graphic design, no text, wide landscape",
    ),
]


def generate_and_save(filename: str, prompt: str) -> bool:
    out_path = OUT_DIR / filename
    if out_path.exists():
        print(f"  [SKIP] {filename} already exists")
        return True

    print(f"  [GEN]  {filename} ...")
    try:
        response = client.images.generate(
            model=DEPLOYMENT,
            prompt=prompt,
            n=1,
            size="1024x1024",
            output_format="jpeg",
        )
        img_data = response.data[0]
        # gpt-image-1 returns b64_json
        if img_data.b64_json:
            raw = base64.b64decode(img_data.b64_json)
            out_path.write_bytes(raw)
            print(f"  [DONE] {filename} ({len(raw)//1024} KB)")
            return True
        elif img_data.url:
            import urllib.request
            urllib.request.urlretrieve(img_data.url, out_path)
            print(f"  [DONE] {filename} (from URL)")
            return True
        else:
            print(f"  [FAIL] {filename}: no image data in response")
            return False
    except Exception as e:
        print(f"  [ERR]  {filename}: {e}")
        return False


def main():
    print(f"Generating {len(IMAGES)} images to: {OUT_DIR}")
    ok = 0
    fail = 0
    for filename, prompt in IMAGES:
        success = generate_and_save(filename, prompt)
        if success:
            ok += 1
        else:
            fail += 1
        time.sleep(1)  # small rate-limit buffer
    print(f"\nDone: {ok} generated, {fail} failed")


if __name__ == "__main__":
    main()
