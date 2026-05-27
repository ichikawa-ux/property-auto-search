"""
Run this once to generate placeholder icons for the Chrome extension.
Requirements: pip install Pillow
Usage: python create_icons.py
"""
import os

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillowをインストールしてください: pip install Pillow")
    raise

os.makedirs("icons", exist_ok=True)

for size in [16, 48, 128]:
    img = Image.new("RGBA", (size, size), (123, 31, 162, 255))  # purple background
    draw = ImageDraw.Draw(img)

    # Draw a simple house shape
    margin = size // 6
    roof_top = (size // 2, margin)
    roof_left = (margin, size // 2)
    roof_right = (size - margin, size // 2)
    draw.polygon([roof_top, roof_left, roof_right], fill=(255, 255, 255, 220))
    body_y = size // 2
    draw.rectangle(
        [margin + size // 8, body_y, size - margin - size // 8, size - margin],
        fill=(255, 255, 255, 200),
    )

    img.save(f"icons/icon{size}.png")
    print(f"Created icons/icon{size}.png")

print("Done! icons/ フォルダにアイコンが作成されました。")
