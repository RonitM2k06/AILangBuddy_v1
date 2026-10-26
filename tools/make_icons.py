"""Renders the app icons (frontend/icons/*.png) from their SVG sources with headless Google Chrome (tests/cdp.py, standard library only).
Run after changing an SVG:  .venv/bin/python tools/make_icons.py
The PNGs are committed, so neither the app nor the tests need Chrome or any image library to serve them."""
import base64
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tests.cdp import Browser  # noqa: E402

ICONS = ROOT / "frontend" / "icons"
OUTPUTS = [("icon.svg", "icon-192.png", 192), ("icon.svg", "icon-512.png", 512), ("icon.svg|square", "apple-touch-icon.png", 180),   # iOS wants it opaque, square
           ("icon.svg", "favicon-32.png", 32), ("icon-maskable.svg", "maskable-192.png", 192), ("icon-maskable.svg", "maskable-512.png", 512)]


def main():
    b = Browser()
    try:
        b.call("Emulation.setDefaultBackgroundColorOverride", color={"r": 0, "g": 0, "b": 0, "a": 0})   # rounded corners stay transparent
        for source, out, size in OUTPUTS:
            name, _, variant = source.partition("|")
            svg = (ICONS / name).read_text()
            if variant == "square":
                svg = svg.replace(' rx="112"', "")                          # no transparent corners: iOS would fill them black
            page = f"<html><body style='margin:0;background:transparent'><img src='data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}' width='{size}' height='{size}' style='display:block'></body></html>"
            b.viewport(size, size, mobile=False)
            b.call("Page.navigate", url="data:text/html;base64," + base64.b64encode(page.encode()).decode())
            time.sleep(0.4)
            data = b.call("Page.captureScreenshot", format="png", clip={"x": 0, "y": 0, "width": size, "height": size, "scale": 1})["data"]
            (ICONS / out).write_bytes(base64.b64decode(data))
            print(out, size)
    finally:
        b.close()


if __name__ == "__main__":
    main()
