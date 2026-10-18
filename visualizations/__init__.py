"""Register the visualized tools served by CourseLight."""
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from moodle import Moodle
from .courses import register_courses
from .coursework import register_coursework
from .schedule import register_schedule
from .deadlines import register_deadlines
from .materials import register_materials
from .gradebook import register_gradebook
from .grade_target import register_grade_target
from .degree_progress import register_degree_progress
from .course_map import register_course_map
from .study_rooms import register_study_rooms


def register_visualizations(mcp: FastMCP, *, get_client: Callable[[], Moodle], clean: Callable[[dict], dict],
                            read_grades: Callable[..., dict]) -> None:
    register_courses(mcp, get_client=get_client)
    register_coursework(mcp, get_client=get_client)
    register_schedule(mcp, clean=clean)
    register_deadlines(mcp, get_client=get_client)
    register_materials(mcp, get_client=get_client)
    register_gradebook(mcp, get_client=get_client, read_grades=read_grades)
    register_grade_target(mcp, get_client=get_client, read_grades=read_grades)
    register_degree_progress(mcp, clean=clean)
    register_course_map(mcp, clean=clean)
    register_study_rooms(mcp)
