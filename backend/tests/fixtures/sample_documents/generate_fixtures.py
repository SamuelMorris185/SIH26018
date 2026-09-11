import os
import io
import pypdf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FIXTURES_DIR = os.path.dirname(os.path.abspath(__file__))

def get_font(size: int = 26):
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def create_clean_record_image() -> str:
    path = os.path.join(FIXTURES_DIR, "clean_land_record.png")
    font = get_font(28)
    img = Image.new("RGB", (1600, 1050), color="white")
    d = ImageDraw.Draw(img)
    text = (
        "GOVERNMENT OF MADHYA PRADESH\n"
        "REVENUE DEPARTMENT - RECORD OF RIGHTS\n\n"
        "State: Madhya Pradesh\n"
        "District: Bhopal\n"
        "Tehsil: Huzur\n"
        "Village: Bairagarh\n"
        "Khasra No: 104/2\n"
        "Khata No: 45\n"
        "Area: 1.2500 ha\n"
        "Classification: Agricultural\n"
        "Name of Owner: Ram Prasad Sharma\n"
        "Co-owner: Shyam Prasad Sharma\n"
        "Registration No: REG-2024-MP-00123\n"
        "Patta No: PATTA-2024-889\n"
        "Mutation No: MUT-2024-00456\n"
        "Document Date: 2024-01-15"
    )
    d.text((60, 60), text, fill="black", font=font)
    img.save(path, format="PNG")
    return path

def create_noisy_record_image() -> str:
    path = os.path.join(FIXTURES_DIR, "noisy_land_record.png")
    font = get_font(18)
    img = Image.new("RGB", (1200, 800), color=(240, 240, 235))
    d = ImageDraw.Draw(img)
    text = (
        "GOVERNMENT OF MADHYA PRADESH\n"
        "Khasra No: 104/2\n"
        "Area: 1.25 ha\n"
    )
    d.text((50, 50), text, fill=(80, 80, 80), font=font)
    # Apply severe blur to simulate water damage / camera blur
    blurred = img.filter(ImageFilter.GaussianBlur(7))
    blurred.save(path, format="PNG")
    return path

def create_conflicting_record_image() -> str:
    path = os.path.join(FIXTURES_DIR, "conflicting_land_record.png")
    font = get_font(28)
    img = Image.new("RGB", (1600, 1050), color="white")
    d = ImageDraw.Draw(img)
    text = (
        "GOVERNMENT OF MADHYA PRADESH\n"
        "REVENUE DEPARTMENT - RECORD OF RIGHTS\n\n"
        "State: Madhya Pradesh\n"
        "District: Bhopal\n"
        "Tehsil: Huzur\n"
        "Village: Bairagarh\n"
        "Khasra No: 104/2\n"
        "Khata No: 45\n"
        "Area: 3.5000 ha\n"
        "Classification: Commercial\n"
        "Name of Owner: Vikram Aditya Singh\n"
        "Co-owner: Rajesh Kumar\n"
        "Registration No: REG-2024-MP-00999\n"
        "Patta No: PATTA-2024-889\n"
        "Mutation No: MUT-2024-00888\n"
        "Document Date: 2024-03-10"
    )
    d.text((60, 60), text, fill="black", font=font)
    img.save(path, format="PNG")
    return path

def create_duplicate_record_image() -> str:
    path = os.path.join(FIXTURES_DIR, "duplicate_land_record.png")
    font = get_font(28)
    img = Image.new("RGB", (1600, 1050), color="white")
    d = ImageDraw.Draw(img)
    text = (
        "GOVERNMENT OF MADHYA PRADESH\n"
        "REVENUE DEPARTMENT - RECORD OF RIGHTS\n\n"
        "State: Madhya Pradesh\n"
        "District: Bhopal\n"
        "Tehsil: Huzur\n"
        "Village: Bairagarh\n"
        "Khasra No: 104/2\n"
        "Khata No: 45\n"
        "Area: 1.2500 ha\n"
        "Classification: Agricultural\n"
        "Name of Owner: Ram Prasad Sharma\n"
        "Co-owner: Shyam Prasad Sharma\n"
        "Registration No: REG-2024-MP-00123\n"
        "Patta No: PATTA-2024-889\n"
        "Mutation No: MUT-2024-00456\n"
        "Document Date: 2024-01-15"
    )
    d.text((60, 60), text, fill="black", font=font)
    img.save(path, format="PNG")
    return path

def create_digital_pdf() -> str:
    path = os.path.join(FIXTURES_DIR, "clean_digital_record.pdf")
    # Generate minimal valid PDF with text stream using pure python
    # We can create a simple PDF page or use pypdf if it can write text, or construct PDF stream
    # A standard digital PDF text stream:
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 380 >>\nstream\n"
        b"BT\n/F1 12 Tf\n50 720 Td\n(GOVERNMENT OF MADHYA PRADESH) Tj\n"
        b"0 -20 Td (State: Madhya Pradesh) Tj\n"
        b"0 -20 Td (District: Bhopal) Tj\n"
        b"0 -20 Td (Tehsil: Huzur) Tj\n"
        b"0 -20 Td (Village: Bairagarh) Tj\n"
        b"0 -20 Td (Khasra No: 104/2) Tj\n"
        b"0 -20 Td (Khata No: 45) Tj\n"
        b"0 -20 Td (Area: 1.2500 ha) Tj\n"
        b"0 -20 Td (Classification: Agricultural) Tj\n"
        b"0 -20 Td (Name of Owner: Ram Prasad Sharma) Tj\n"
        b"0 -20 Td (Registration No: REG-2024-MP-00123) Tj\n"
        b"ET\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000676 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n747\n%%EOF\n"
    )
    with open(path, "wb") as f:
        f.write(pdf_content)
    return path

def create_corrupt_file() -> str:
    path = os.path.join(FIXTURES_DIR, "corrupt_record.png")
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00CORRUPT_BYTE_GARBAGE\xff\xfe\x00")
    return path

def generate_all_fixtures():
    os.makedirs(FIXTURES_DIR, exist_ok=True)
    c = create_clean_record_image()
    n = create_noisy_record_image()
    cf = create_conflicting_record_image()
    d = create_duplicate_record_image()
    p = create_digital_pdf()
    cr = create_corrupt_file()
    print(f"Generated fixtures in {FIXTURES_DIR}:")
    for fp in [c, n, cf, d, p, cr]:
        print(f" - {os.path.basename(fp)} ({os.path.getsize(fp)} bytes)")

if __name__ == "__main__":
    generate_all_fixtures()
