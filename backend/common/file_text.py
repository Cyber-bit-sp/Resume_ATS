import re
import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

from rest_framework import serializers


ALLOWED_TEXT_UPLOAD_EXTENSIONS = {".doc", ".docx", ".pdf", ".txt"}
MAX_TEXT_UPLOAD_SIZE = 5 * 1024 * 1024


def validate_text_upload(file_obj):
    extension = Path(file_obj.name).suffix.lower()
    if extension not in ALLOWED_TEXT_UPLOAD_EXTENSIONS:
        raise serializers.ValidationError("Upload a .doc, .docx, .pdf, or .txt file.")
    if file_obj.size > MAX_TEXT_UPLOAD_SIZE:
        raise serializers.ValidationError("Uploaded file is too large.")
    return file_obj


def extract_text_from_upload(file_obj):
    extension = Path(file_obj.name).suffix.lower()
    raw = file_obj.read()
    file_obj.seek(0)

    if extension == ".txt":
        return _decode_text(raw)
    if extension == ".pdf":
        return _extract_pdf_text(file_obj)
    if extension == ".docx":
        text = _extract_docx_text(raw)
        if text:
            return text
        raise serializers.ValidationError("Could not read text from that DOCX file.")
    if extension == ".doc":
        return _extract_doc_text(raw)
    raise serializers.ValidationError("Upload a .doc, .docx, .pdf, or .txt file.")


def _decode_text(raw):
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore").strip()


def _extract_pdf_text(file_obj):
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise serializers.ValidationError("PDF uploads require the pypdf package on the backend.") from exc

    try:
        reader = PdfReader(file_obj)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        raise serializers.ValidationError("Could not read text from that PDF file.") from exc


def _extract_doc_text(raw):
    if zipfile.is_zipfile(BytesIO(raw)):
        text = _extract_docx_text(raw)
        if text:
            return text

    if raw.startswith(b"\xd0\xcf\x11\xe0"):
        text = _extract_binary_doc_strings(raw)
        if text:
            return text

    decoded = _decode_text(raw)
    if decoded.lstrip().startswith("{\\rtf"):
        decoded = _strip_rtf(decoded)
    else:
        decoded = re.sub(r"<[^>]+>", " ", decoded)
    decoded = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", decoded)
    decoded = re.sub(r"[ \t]+", " ", decoded)
    decoded = re.sub(r"\n\s*\n\s*\n+", "\n\n", decoded)
    return decoded.strip()


def _extract_binary_doc_strings(raw):
    ascii_chunks = re.findall(rb"[A-Za-z0-9][A-Za-z0-9\s.,;:!?()/%&@#'\"+\-\n\r]{24,}", raw)
    utf16_chunks = re.findall((rb"(?:[\x20-\x7e]\x00){12,}"), raw)
    parts = [chunk.decode("latin-1", errors="ignore") for chunk in ascii_chunks]
    parts.extend(chunk.decode("utf-16le", errors="ignore") for chunk in utf16_chunks)
    text = "\n".join(parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def _extract_docx_text(raw):
    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile):
        return ""

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ElementTree.fromstring(xml)
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        parts = [node.text for node in paragraph.findall(".//w:t", namespace) if node.text]
        if parts:
            paragraphs.append("".join(parts))
    return "\n".join(paragraphs).strip()


def _strip_rtf(value):
    value = re.sub(r"{\\\*?\\[^{}]+}|[{}]", " ", value)
    value = re.sub(r"\\'[0-9a-fA-F]{2}", " ", value)
    value = re.sub(r"\\[a-zA-Z]+\d* ?", " ", value)
    return value
