"""The setup QR code, made locally with the vendored qrcodegen (backend/vendor/README.md). No network, no image service.

The result is a plain matrix: a list of rows, each a string of "1" (dark) and "0" (light). The frontend draws it; nothing in it is
markup, so nothing can be injected through it. The manual setup key is always offered as well, so 2FA works without the QR code."""
from ..vendor.qrcodegen import QrCode


def matrix(text: str) -> dict:
    qr = QrCode.encode_text(text, QrCode.Ecc.MEDIUM)
    size = qr.get_size()
    return {"size": size, "modules": ["".join("1" if qr.get_module(x, y) else "0" for x in range(size)) for y in range(size)]}
