# Vendored third-party code

Code copied into the repository unmodified, so it is used locally with no network, CDN or runtime package.

| File | Project | Version | Source | License | SHA-256 |
|---|---|---|---|---|---|
| `qrcodegen.py` | QR Code generator library (Python), Project Nayuki | 1.8.0 | PyPI sdist `qrcodegen-1.8.0.zip` (https://www.nayuki.io/page/qr-code-generator-library) | MIT; the copyright and permission notice is kept in the file header | `b089855caf16185c61421ea4927c1b213cf9468940d71fa8ab11ef83662dcc84` |

`qrcodegen.py` uses only the Python standard library. LingoBuddy uses it through `backend/auth/qr.py` to turn the TOTP `otpauth://` URI into a module matrix. Do not edit it here: replace it with a newer upstream copy, and update the table, if needed.
