"""Read-only Gradescope reads, using the session saved by `login.py --gradescope`.

Gradescope has no public student API, so these read its web pages with the
saved cookies: courses, and each course's assignments with status, score, and
dates. There is no uploading or submitting, and quiz or online-assignment
questions are never read. Submit work yourself in Gradescope.
"""
from __future__ import annotations

from html.parser import HTMLParser
import json
import logging
import re
from urllib.parse import urlsplit

import httpx

from lehigh import SESSION_PATH as LEHIGH_SESSION
from moodle import MoodleError


BASE = 'https://www.gradescope.com'
HOST = 'www.gradescope.com'
SESSION_PATH = LEHIGH_SESSION.parent / 'gradescope_state.json'
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}
# A course code like "CSE 303", "CSE-303-010-FL26", or "CSE326[Fall25]", for matching CourseSite courses.
COURSE_CODE = re.compile(r'(?<![A-Za-z])([A-Za-z]{2,4})[\s_-]?(\d{3})(?!\d)')

for _name in ('httpx', 'httpcore'):
    # Match moodle.py: no transport logs with URLs or response fragments.
    logging.getLogger(_name).disabled = True


class GradescopeError(MoodleError):
    """A Gradescope failure, reported in the same envelope as Moodle errors."""


def _not_signed_in():
    return GradescopeError('gradescope_not_signed_in',
                           'Not signed in to Gradescope. Call login_gradescope to sign in.')


def _expired():
    return GradescopeError('gradescope_sign_in_expired',
                           'The Gradescope sign-in expired. Call login_gradescope to sign in again.')


# HTML

class Node:
    def __init__(self, tag: str, attrs: dict, parent: Node | None):
        self.tag, self.attrs, self.parent, self.children = tag, attrs, parent, []

    def classes(self) -> set[str]:
        return set((self.attrs.get('class') or '').split())

    def text(self) -> str:
        parts = [child if isinstance(child, str) else child.text() for child in self.children]
        return ' '.join(' '.join(parts).split())

    def iter(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.iter()

    def find_all(self, tag: str | None = None, cls: str | None = None, **attrs):
        for node in self.iter():
            if ((tag is None or node.tag == tag) and (cls is None or cls in node.classes())
                    and all(node.attrs.get(key) == value for key, value in attrs.items())):
                yield node

    def find(self, tag: str | None = None, cls: str | None = None, **attrs):
        return next(self.find_all(tag, cls, **attrs), None)


class Tree(HTMLParser):
    """Build a small element tree; nothing is executed or fetched."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = self.current = Node('#root', {}, None)
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {key: value or '' for key, value in attrs}, self.current)
        self.current.children.append(node)
        if tag not in VOID_TAGS:
            self.current = node
        if tag in {'script', 'style'}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self.skip = max(0, self.skip - 1)
        node = self.current
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self.current = node.parent  # Tolerate unclosed tags by unwinding to the match.

    def handle_data(self, data):
        if not self.skip:
            self.current.children.append(data)


def _parse(text: str) -> Node:
    tree = Tree()
    tree.feed(text)
    tree.close()
    return tree.root


# Session

def _client(timeout: float = 30) -> httpx.Client:
    if not SESSION_PATH.exists():
        raise _not_signed_in()
    try:
        state = json.loads(SESSION_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise _not_signed_in() from None
    cookies = httpx.Cookies()
    for cookie in state.get('cookies', []):
        if cookie.get('domain', '').lstrip('.').endswith('gradescope.com'):
            cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'], path=cookie.get('path', '/'))
    return httpx.Client(base_url=BASE, cookies=cookies, timeout=timeout, trust_env=False, follow_redirects=True,
                        headers={'User-Agent': 'CourseLight'})


def _checked(response: httpx.Response) -> httpx.Response:
    url = urlsplit(str(response.url))
    if url.hostname != HOST or url.path.rstrip('/') in {'', '/login'}:
        raise _expired()  # Signed-out requests land on the login or home page.
    if response.status_code in {401, 403}:
        raise GradescopeError('gradescope_forbidden', 'Gradescope denied access to this page for the signed-in account.')
    if response.status_code == 404:
        raise GradescopeError('gradescope_not_found', 'This Gradescope course or assignment was not found for the signed-in account.')
    if response.status_code != 200:
        raise GradescopeError('gradescope_unavailable', 'Gradescope is unavailable right now. Try again later.')
    return response


def _get(client: httpx.Client, path: str) -> Node:
    try:
        return _parse(_checked(client.get(path)).text)
    except httpx.HTTPError:
        raise GradescopeError('gradescope_unavailable', 'Gradescope could not be reached. Try again later.') from None


# Reads

def _field(node: Node, cls: str) -> str | None:
    found = node.find(cls=cls)
    return found.text() if found is not None else None


def list_courses() -> dict:
    with _client() as client:
        page = _get(client, '/account')
    courses, role, term = [], None, None
    for node in page.iter():
        classes = node.classes()
        if 'pageHeading' in classes:
            heading = node.text().lower()
            role = 'instructor' if 'instructor' in heading else 'student' if 'student' in heading else role
        elif 'courseList--term' in classes:
            term = node.text()
        elif node.tag == 'a' and 'courseBox' in classes and (match := re.fullmatch(r'/courses/(\d+)', node.attrs.get('href', ''))):
            courses.append({'course_id': match.group(1), 'short_name': _field(node, 'courseBox--shortname'),
                            'name': _field(node, 'courseBox--name'), 'term': term, 'role': role or 'student',
                            'assignments': _field(node, 'courseBox--assignments'),
                            'url': f'{BASE}/courses/{match.group(1)}'})
    return {'courses': courses}


def _time(row: Node, cls: str) -> list[str]:
    return [node.attrs.get('datetime') or node.text() for node in row.find_all('time', cls=cls)]


def list_assignments(course_id: str) -> dict:
    with _client() as client:
        page = _get(client, f'/courses/{course_id}')
    table = page.find('table', id='assignments-student-table')
    if table is None:
        raise GradescopeError('gradescope_no_student_view',
                              'No student assignment list was found for this course. It may be an instructor course.')
    title = _field(page, 'courseHeader--title')
    assignments = []
    for row in table.find_all('tr'):
        cells = [child for child in row.children if isinstance(child, Node) and child.tag in {'th', 'td'}]
        if not cells or row.find('th', scope='col') is not None:
            continue
        link = cells[0].find('a')
        button = cells[0].find(cls='js-submitAssignment')
        href = link.attrs.get('href', '') if link is not None else ''
        match = re.search(r'/assignments/(\d+)', href)
        assignment_id = match.group(1) if match else (button.attrs.get('data-assignment-id') if button is not None else None)
        status = row.find(cls='submissionStatus')
        score = row.find(cls='submissionStatus--score')
        due = _time(row, 'submissionTimeChart--dueDate')
        assignments.append({
            'assignment_id': assignment_id,
            'name': cells[0].text(),
            'status': status.text() if status is not None else (cells[1].text() if len(cells) > 1 else None),
            'score': score.text() if score is not None else None,
            'released': next(iter(_time(row, 'submissionTimeChart--releaseDate')), None),
            'due': due[0] if due else None,
            'late_due': due[1] if len(due) > 1 else None,
            'submission_url': f'{BASE}{href}' if '/submissions/' in href else None,
            'url': f'{BASE}/courses/{course_id}/assignments/{assignment_id}' if assignment_id else None,
        })
    return {'course_id': course_id, 'course': title,
            'assignments': assignments, 'url': f'{BASE}/courses/{course_id}',
            'note': 'Times are Gradescope datetimes with UTC offsets. A missing score is not a zero.'}



def course_codes(*texts: str | None) -> set[str]:
    """Course codes in names like "CSE-303-010-FL26", normalized to "CSE 303"."""
    return {f'{subject.upper()} {number}' for text in texts if text
            for subject, number in COURSE_CODE.findall(text)}


def scored(course_id: str) -> dict:
    """One course's assignments reduced to grades: score, status, and due date."""
    data = list_assignments(course_id)
    return {'course_id': course_id, 'course': data['course'], 'url': data['url'],
            'assignments': [{key: item[key] for key in ('name', 'score', 'status', 'due', 'url')}
                            for item in data['assignments']],
            'note': 'Only released scores appear. A missing score is not a zero, and "Submitted" does not mean graded.'}
