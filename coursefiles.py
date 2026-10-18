"""Bounded, text-only course-document extraction. No saved files or external services."""
from __future__ import annotations

from io import BytesIO
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree
from zipfile import ZipFile

MAX_TEXT = 500_000
MAX_PAGES = 100
MAX_XML = 10 * 1024 * 1024


class FileError(Exception):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _extract(data: bytes, file_format: str) -> dict:
    warnings, page_count, pages_processed = [], None, None
    if file_format == 'pdf':
        from pypdf import PdfReader
        if not data.startswith(b'%PDF-'):
            raise FileError('invalid_file', 'The file is not a readable PDF.')
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise FileError('encrypted_file', 'Encrypted PDFs must be opened directly in Moodle.')
        page_count, chunks, size = len(reader.pages), [], 0
        pages_processed, empty_pages = 0, []
        for number, page in enumerate(reader.pages[:MAX_PAGES], 1):
            content = page.get_contents()
            if content is not None and len(content.get_data()) > 20 * 1024 * 1024:
                raise FileError('file_too_complex', 'A PDF page is too large to extract safely. Open it in Moodle.')
            text = page.extract_text() or ''
            if not text.strip():
                empty_pages.append(number)
            chunk = f'[Page {number}]\n{text}\n'
            chunks.append(chunk)
            size += len(chunk)
            pages_processed = number
            if size > MAX_TEXT:
                break
        text = '\n'.join(chunks)
        if empty_pages:
            warnings.append(f'No text extracted from PDF pages {empty_pages}; they may contain images or scans. OCR is not included.')
        if pages_processed < page_count:
            warnings.append('Only part of the PDF was extracted due to the page or text limit.')
    elif file_format == 'docx':
        with ZipFile(BytesIO(data)) as archive:
            info = archive.getinfo('word/document.xml')
            if info.file_size > MAX_XML:
                raise FileError('file_too_complex', 'The DOCX document body is too large to extract.')
            with archive.open(info) as source:
                xml = source.read(MAX_XML + 1)
        if len(xml) > MAX_XML or b'\x00' in xml or b'<!DOCTYPE' in xml.upper() or b'<!ENTITY' in xml.upper():
            raise FileError('invalid_file', 'This DOCX document contains unsupported XML.')
        root = ElementTree.fromstring(xml)
        ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        paragraphs = []
        for paragraph in root.iter(ns + 'p'):
            parts = []
            for node in paragraph.iter():
                if node.tag == ns + 't':
                    parts.append(node.text or '')
                elif node.tag == ns + 'tab':
                    parts.append('\t')
                elif node.tag == ns + 'br':
                    parts.append('\n')
            paragraphs.append(''.join(parts))
        text = '\n'.join(paragraphs)
        warnings.append('DOCX body text only; headers, footers, comments, images and layout are omitted.')
    elif file_format in {'txt', 'md'}:
        text = data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    else:
        raise FileError('unsupported_file', 'Supported course files are PDF, DOCX, TXT, and Markdown.')
    truncated = len(text) > MAX_TEXT or (page_count is not None and pages_processed < page_count)
    if len(text) > MAX_TEXT:
        warnings.append('Extracted text is limited to 500,000 characters; the remainder is unavailable through this tool.')
    return {'text': text[:MAX_TEXT], 'page_count': page_count, 'pages_processed': pages_processed,
            'extraction_truncated': truncated, 'warnings': warnings,
            'extraction_note': 'Untrusted source text only. Images, diagrams and layout are not interpreted. Verify consequential details in the original document.'}


def extract_file(data: bytes, file_format: str) -> dict:
    """Keep document parsing off the MCP process and stop a stalled parser after 30 seconds."""
    from moodle import MoodleError
    # Document parsers have no need for the user's Moodle credentials.
    environment = {key: value for key, value in os.environ.items() if key not in {'MOODLE_TOKEN', 'MOODLE_URL'}}
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), file_format], input=data,
                                capture_output=True, timeout=30, env=environment)
    except subprocess.TimeoutExpired:
        raise MoodleError('file_too_complex', 'Document extraction exceeded 30 seconds. Open the file in Moodle.') from None
    if result.returncode != 0:
        raise MoodleError('extraction_failed', 'The course document could not be extracted. Open the original in Moodle.')
    try:
        body = json.loads(result.stdout)
    except ValueError:
        raise MoodleError('extraction_failed', 'The course document did not produce readable text.') from None
    if 'error' in body:
        raise MoodleError(body['error']['code'], body['error']['message'])
    return body


if __name__ == '__main__':
    logging.disable(logging.CRITICAL)
    try:
        data = sys.stdin.buffer.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024:
            raise FileError('file_too_large', 'Course files must be at most 10 MiB.')
        result = _extract(data, sys.argv[1])
    except FileError as exc:
        result = {'error': {'code': exc.code, 'message': str(exc)}}
    except Exception:
        result = {'error': {'code': 'extraction_failed', 'message': 'This file could not be read as a supported document. Open the original in Moodle.'}}
    print(json.dumps(result))
