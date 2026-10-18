"""Register the visualized tools served by CourseLight."""
from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from moodle import Moodle
from .courses import register_courses
from .coursework import register_coursework
from .schedule import register_schedule


def register_visualizations(mcp: FastMCP, *, get_client: Callable[[], Moodle], clean: Callable[[dict], dict]) -> None:
    register_courses(mcp, get_client=get_client)
    register_coursework(mcp, get_client=get_client)
    register_schedule(mcp, clean=clean)
