"""Generate print-ready QR codes for Sloane Connect May 2026 (Mhare logo centred)."""

from __future__ import annotations

from pathlib import Path

import qrcode
from PIL import Image
from qrcode.constants import ERROR_CORRECT_H

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'static' / 'Assets' / 'Expo QR'
LOGO_PATH = ROOT / 'static' / 'Assets' / 'Digital logos' / 'PNG' / '2000w' / 'Mhare Consulting_Primary Icon.png'

BASE_URL = 'https://mharetech.co.za/expo'

SOURCES = {
    'mytrack': 'myTrack',
    'myroutes': 'myRoutes',
    'kasistock': 'KasiStock',
    'general': 'Mhare Tech (general)',
}

# Logo covers ~22% of QR width; H correction keeps codes scannable
LOGO_RATIO = 0.22
LOGO_PAD_RATIO = 0.14


def embed_logo(qr_img: Image.Image, logo_path: Path) -> Image.Image:
    """Place brand icon on a white pad in the centre of the QR."""
    qr_rgb = qr_img.convert('RGB')
    width, height = qr_rgb.size
    logo = Image.open(logo_path).convert('RGBA')

    logo_size = int(min(width, height) * LOGO_RATIO)
    logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

    pad = int(logo_size * LOGO_PAD_RATIO)
    box_size = logo_size + pad * 2
    white_box = Image.new('RGB', (box_size, box_size), '#ffffff')
    offset = (pad, pad)
    white_box.paste(logo, offset, logo)

    position = ((width - box_size) // 2, (height - box_size) // 2)
    qr_rgb.paste(white_box, position)
    return qr_rgb


def make_qr(url: str, out_path: Path, box_size: int = 12, border: int = 2) -> None:
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='#0b0146', back_color='#ffffff')
    if LOGO_PATH.is_file():
        img = embed_logo(img, LOGO_PATH)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f'Wrote {out_path} ({url})')


def main() -> None:
    if not LOGO_PATH.is_file():
        print(f'Warning: logo not found at {LOGO_PATH} — QR without centre logo')
    for src, label in SOURCES.items():
        url = f'{BASE_URL}?src={src}'
        filename = f'expo-qr-{src}.png'
        make_qr(url, OUT_DIR / filename)
    readme = OUT_DIR / 'README.txt'
    readme.write_text(
        'Sloane Connect May 2026 — QR codes for mharetech.co.za/expo (Mhare icon centred)\n'
        'Regenerate: python scripts/generate_expo_qr.py\n\n'
        + '\n'.join(f'{name}: {BASE_URL}?src={key}' for key, name in SOURCES.items())
        + '\n',
        encoding='utf-8',
    )
    print(f'Wrote {readme}')


if __name__ == '__main__':
    main()
