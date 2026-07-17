import datetime
import shutil
from pathlib import Path

import cv2
import numpy as np
import pyautogui
from PIL import Image, ImageStat


BASE_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = BASE_DIR / "screenshots"


def resolve_path(path_text):
    path = Path(str(path_text).strip().strip('"').strip("'")).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


def capture_screenshot():
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    filename = f"screen_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    path = SCREENSHOT_DIR / filename
    image = pyautogui.screenshot()
    image.save(path)
    return str(path)


def image_metadata(path_text):
    path = resolve_path(path_text)
    with Image.open(path) as image:
        return {
            "path": str(path),
            "format": image.format,
            "mode": image.mode,
            "width": image.width,
            "height": image.height,
            "size_bytes": path.stat().st_size,
        }


def analyze_image(path_text):
    path = resolve_path(path_text)
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        stat = ImageStat.Stat(rgb)
        mean = tuple(round(value, 1) for value in stat.mean)
        brightness = round(sum(mean) / 3, 1)
        colors = dominant_colors(rgb)

    return {
        **image_metadata(path),
        "average_rgb": mean,
        "brightness": brightness,
        "brightness_label": brightness_label(brightness),
        "dominant_colors": colors,
        "summary": format_image_summary(path, mean, brightness, colors),
    }


def dominant_colors(image, count=5):
    sample = image.copy()
    sample.thumbnail((120, 120))
    quantized = sample.quantize(colors=count).convert("RGB")
    color_counts = quantized.getcolors(maxcolors=120 * 120) or []
    color_counts.sort(reverse=True, key=lambda item: item[0])
    total = sum(item[0] for item in color_counts) or 1

    return [
        {
            "rgb": item[1],
            "hex": "#{:02x}{:02x}{:02x}".format(*item[1]),
            "percent": round((item[0] / total) * 100, 1),
        }
        for item in color_counts[:count]
    ]


def brightness_label(value):
    if value < 70:
        return "dark"
    if value > 185:
        return "bright"
    return "balanced"


def format_image_summary(path, mean, brightness, colors):
    dominant = colors[0]["hex"] if colors else "unknown"
    return (
        f"{Path(path).name} is a {brightness_label(brightness)} image. "
        f"Average RGB is {mean}; dominant color is {dominant}."
    )


def ocr_image(path_text):
    tesseract = shutil.which("tesseract")
    if not tesseract:
        return {
            "available": False,
            "text": "",
            "error": "Tesseract OCR engine is not installed or not on PATH.",
        }

    try:
        import pytesseract
    except ImportError:
        return {"available": False, "text": "", "error": "pytesseract is not installed."}

    path = resolve_path(path_text)
    with Image.open(path) as image:
        text = pytesseract.image_to_string(image)

    return {"available": True, "text": text.strip(), "error": None}


def decode_qr(path_text):
    path = resolve_path(path_text)
    image = cv2.imread(str(path))
    if image is None:
        return {"items": [], "error": "Could not read image."}

    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(image)
    items = []
    if data:
        items.append({"type": "qr", "data": data, "points": points.tolist() if points is not None else None})

    return {"items": items, "error": None}


def decode_barcodes(path_text):
    try:
        from pyzbar.pyzbar import decode
    except Exception as exc:
        return {"items": [], "error": f"Barcode decoder unavailable: {exc}"}

    path = resolve_path(path_text)
    with Image.open(path) as image:
        decoded = decode(image)

    return {
        "items": [
            {
                "type": item.type,
                "data": item.data.decode("utf-8", errors="replace"),
                "rect": {
                    "left": item.rect.left,
                    "top": item.rect.top,
                    "width": item.rect.width,
                    "height": item.rect.height,
                },
            }
            for item in decoded
        ],
        "error": None,
    }


def screen_summary():
    path = capture_screenshot()
    analysis = analyze_image(path)
    ocr = ocr_image(path)
    qr = decode_qr(path)
    return {
        "screenshot": path,
        "analysis": analysis,
        "ocr": ocr,
        "qr": qr,
    }


def compare_images(first_path, second_path):
    first = resolve_path(first_path)
    second = resolve_path(second_path)
    with Image.open(first) as img_a, Image.open(second) as img_b:
        a = img_a.convert("RGB").resize((256, 256))
        b = img_b.convert("RGB").resize((256, 256))
        arr_a = np.asarray(a).astype("float32")
        arr_b = np.asarray(b).astype("float32")
        diff = np.abs(arr_a - arr_b)
        mean_diff = float(diff.mean())

    similarity = round(max(0, 100 - (mean_diff / 255 * 100)), 1)
    return {
        "first": str(first),
        "second": str(second),
        "mean_difference": round(mean_diff, 2),
        "similarity_percent": similarity,
    }
