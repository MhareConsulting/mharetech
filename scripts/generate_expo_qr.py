"""Generate print-ready QR codes for Logistics Expo SA 2026 collateral."""

from __future__ import annotations

from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_H

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'static' / 'Assets' / 'Expo QR'

BASE_URL = 'https://mharetech.co.za/expo'

SOURCES = {
    'mytrack': 'myTrack',
    'myroutes': 'myRoutes',
    'kasistock': 'KasiStock',
    'general': 'Mhare Tech (general)',
}


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
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path)
    print(f'Wrote {out_path} ({url})')


def main() -> None:
    for src, label in SOURCES.items():
        url = f'{BASE_URL}?src={src}'
        filename = f'expo-qr-{src}.png'
        make_qr(url, OUT_DIR / filename)
    readme = OUT_DIR / 'README.txt'
    readme.write_text(
        'Expo QR codes for mharetech.co.za/expo\n'
        'Regenerate: python scripts/generate_expo_qr.py\n\n'
        + '\n'.join(f'{name}: {BASE_URL}?src={key}' for key, name in SOURCES.items())
        + '\n',
        encoding='utf-8',
    )
    print(f'Wrote {readme}')


if __name__ == '__main__':
    main()
