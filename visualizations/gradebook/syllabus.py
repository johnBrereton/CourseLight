"""Read visible syllabus modules, never arbitrary caller-supplied file URLs."""
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from moodle import Moodle, MoodleError
from ..coursework.discovery import plain_text
from ..materials.service import browser_download
from .models import Syllabus

SYLLABUS = re.compile(r'\bsyllab(?:us|i)\b|\bgrading\s+(?:policy|policies|scheme)\b', re.I)
MAX_BYTES = 5 * 1024 * 1024


def course_name(client: Moodle, course_id: int):
    courses = client.call('core_enrol_get_users_courses', userid=client.identity()['userid'])
    course = next((row for row in courses if row.get('id') == course_id), None)
    if course is None:
        raise ValueError('Choose a course returned by list_courses.')
    name = plain_text(course.get('fullname'))[:240] or 'Gradebook'
    code = plain_text(course.get('shortname'))
    if code and name.startswith(code + '-'):
        name = name[len(code) + 1:] or code
    return name


def course_modules(client: Moodle, course_id: int):
    name = course_name(client, course_id)
    sections = client.clean(client.call('core_course_get_contents', courseid=course_id))
    modules = [module for section in sections
               if section.get('visible') != 0 and section.get('uservisible') is not False
               for module in section.get('modules', [])
               if module.get('visible') != 0 and module.get('uservisible') is not False]
    return name, modules


def fetch_bytes(http, url, params=None):
    with http.stream('GET', url, params=params, follow_redirects=False) as response:
        if response.status_code != 200:
            raise ValueError('This syllabus could not be read. Open its source in CourseSite.')
        content = bytearray()
        for chunk in response.iter_bytes(chunk_size=65536):
            if len(content) + len(chunk) > MAX_BYTES:
                raise ValueError('This syllabus exceeds the 5 MB reading limit.')
            content.extend(chunk)
        return bytes(content), response.headers.get('content-type', '')


def module_text(client: Moodle, course_id: int, module: dict) -> str:
    kind = module['modname']
    if kind == 'page':
        data = client.call('mod_page_get_pages_by_courses', courseids=[course_id])
        page = next((p for p in data.get('pages', [])
                     if p.get('id') == module.get('instance') and p.get('course') == course_id), {})
        return plain_text(page.get('content'))
    if kind == 'label':
        return plain_text(module.get('description'))
    if kind == 'resource':
        files = [f for f in module.get('contents', []) if f.get('type') == 'file'
                 and str(f.get('filename', '')).lower().endswith('.pdf')]
        if len(files) != 1:
            raise ValueError('Select a syllabus resource containing one PDF.')
        browser_url = browser_download(client.url, files[0].get('fileurl', ''))
        if not browser_url:
            raise ValueError('The syllabus file is not a supported CourseSite resource.')
        path = browser_url.split('?', 1)[0].removeprefix(client.url + '/pluginfile.php/')
        content, _ = fetch_bytes(client.http, client.url + '/webservice/pluginfile.php/' + path,
                                 {'token': client.token})
        if not content.startswith(b'%PDF-'):
            raise ValueError('CourseSite did not return a readable syllabus PDF.')
        result = subprocess.run([sys.executable, '-I', '-B', str(Path(__file__).with_name('pdf_text.py'))],
                                input=content, capture_output=True, timeout=15)
        if result.returncode:
            raise ValueError('The syllabus PDF could not be extracted within the reading limits.')
        return result.stdout.decode('utf-8')
    if kind == 'url':
        urls = [f.get('fileurl', '') for f in module.get('contents', []) if f.get('type') == 'url']
        for url in urls:
            parts = urlsplit(url)
            match = re.fullmatch(r'/document/d/([\w-]+)/(?:edit|view|preview)', parts.path)
            if parts.scheme == 'https' and parts.netloc == 'docs.google.com' and match:
                # Public text export only. No CourseSite token or saved browser cookies are sent.
                with httpx.Client(timeout=20, trust_env=False) as http:
                    content, kind = fetch_bytes(http, f'https://docs.google.com/document/d/{match[1]}/export',
                                                {'format': 'txt'})
                if not kind.startswith('text/plain'):
                    raise ValueError('This linked syllabus requires browser access. Open its source.')
                text = content.decode('utf-8-sig')
                if len(text) > 60000:
                    raise ValueError('The syllabus exceeds the text reading limit.')
                return text
    raise ValueError('This syllabus format needs to be opened in the browser.')


def read_syllabi(client: Moodle, course_id: int, modules: list[dict], selected: int | None = None):
    candidates = [m for m in modules if m.get('modname') in {'resource', 'page', 'url', 'label'}
                  and SYLLABUS.search(plain_text(m.get('name')))]
    if selected is not None:
        candidates = [m for m in candidates if m.get('id') == selected]
        if not candidates:
            raise ValueError('Select a visible syllabus or grading-policy module from this course.')
    output = []
    for module in candidates[:6]:
        source = Syllabus(module_id=module['id'], title=plain_text(module.get('name'))[:240],
                          url=(f'{client.url}/course/view.php?id={course_id}' if module['modname'] == 'label'
                               else f'{client.url}/mod/{module["modname"]}/view.php?id={module["id"]}'))
        try:
            source.text = client.clean(module_text(client, course_id, module)).strip()[:60000]
            if not source.text:
                source.notice = 'No readable syllabus text was found; scanned PDFs need manual review.'
        except (MoodleError, ValueError, httpx.HTTPError, subprocess.TimeoutExpired, OSError, UnicodeError):
            source.notice = 'Syllabus text is unavailable. Open the source to check the grading policy.'
        output.append(source)
    return output
