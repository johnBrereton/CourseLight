"""Read selected learning resources without downloading files or exposing tokens."""
import re
from urllib.parse import unquote

from moodle import Moodle, MoodleError
from ..coursework.discovery import plain_text
from .models import Material, MaterialGroup, MaterialsQuery, MaterialsView

KINDS = frozenset({'resource', 'folder', 'page', 'url', 'book'})


def browser_download(site: str, value: str) -> str | None:
    # Moodle documents identical paths for web-service and browser file endpoints.
    for prefix in (site + '/webservice/pluginfile.php/', site + '/pluginfile.php/'):
        if value.startswith(prefix):
            path = value[len(prefix):].split('?', 1)[0].split('#', 1)[0]
            decoded = unquote(path)
            if (re.fullmatch(r'\d+/mod_(resource|folder)/content/\d+/.+', path)
                    and not any(part in {'.', '..'} for part in decoded.split('/'))
                    and not any(c in decoded for c in '\r\n\\')):
                url = f'{site}/pluginfile.php/{path}?forcedownload=1'
                return url if len(url) <= 2048 else None
    return None


def get_materials(client: Moodle, query: MaterialsQuery) -> MaterialsView:
    enrolled = client.call('core_enrol_get_users_courses', userid=client.identity()['userid'])
    course = next((item for item in enrolled if item.get('id') == query.course_id), None)
    if course is None:
        raise ValueError('Choose a course returned by list_courses.')
    sections = client.clean(client.call('core_course_get_contents', courseid=query.course_id))
    if not isinstance(sections, list):
        raise MoodleError('invalid_response', 'CourseSite did not return course materials.')
    modules = {}
    for section in sections:
        if section.get('uservisible') is False or section.get('visible') == 0:
            continue
        section_name = plain_text(section.get('name'))[:240] or 'Course materials'
        for module in section.get('modules', []):
            if (module.get('modname') in KINDS and module.get('uservisible') is not False
                    and module.get('visible') != 0):
                modules[module['id']] = (section_name, module)

    groups = []
    for selection in query.groups:
        items = []
        missing = False
        for module_id in selection.module_ids:
            if module_id not in modules:
                missing = True
                continue
            section, module = modules[module_id]
            name = plain_text(module.get('name'))[:240] or 'Course material'
            source = f'{client.url}/mod/{module["modname"]}/view.php?id={module_id}'
            files = []
            if module['modname'] in {'resource', 'folder'}:
                for entry in module.get('contents', []):
                    url = browser_download(client.url, entry.get('fileurl', '')) if entry.get('type') == 'file' else None
                    if url:
                        files.append(Material(module_id=module_id, name=name, section=section, source_url=source,
                                              filename=plain_text(entry.get('filename'))[:240] or name,
                                              size=entry.get('filesize'), download_url=url))
            items.extend(files or [Material(module_id=module_id, name=name, section=section, source_url=source)])
        notices = []
        if missing:
            notices.append('Some selected materials are unavailable. Open CourseSite to check.')
        if len(items) > 60:
            notices.append('Showing the first 60 files in this group. Open CourseSite for the rest.')
        groups.append(MaterialGroup(title=selection.title, items=items[:60], notice=' '.join(notices) or None))
    view = MaterialsView(course_id=query.course_id,
                         course_name=plain_text(course.get('fullname'))[:240] or 'Course materials',
                         site_url=client.url, groups=groups)
    return MaterialsView.model_validate(client.clean(view.model_dump(mode='json')))
