"""Register the separate interactive grade-target resource and tool."""
from collections.abc import Callable
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import ValidationError

from moodle import Moodle, MoodleError
from ..courses.models import PositiveID
from ..gradebook.resource import READ, GradescopeID
from ..resources import component_html
from .models import GradeTargetView, GradingPlan, Percent
from .service import get_grade_target

RESOURCE_URI = 'ui://courselight/grade_target/v1.html'


def register_grade_target(mcp: FastMCP, *, get_client: Callable[[], Moodle], read_grades: Callable[..., dict]):
    @mcp.resource(RESOURCE_URI, name='grade_target', title='Grade target', mime_type='text/html;profile=mcp-app',
                  meta={'ui': {'prefersBorder': False,
                               'csp': {'connectDomains': [], 'resourceDomains': [], 'frameDomains': []}},
                        'openai/ui': {'availableDisplayModes': ['inline']},
                        'openai/widgetDescription': 'Draggable score bars and a projected final grade based on documented syllabus weights.'})
    def grade_target_resource() -> str:
        return component_html('grade_target')

    @mcp.tool(title='Grade target', annotations=READ, structured_output=True,
              meta={'ui': {'resourceUri': RESOURCE_URI},
                    'openai/toolInvocation/invoking': 'Calculating your grade target…',
                    'openai/toolInvocation/invoked': 'Grade target ready'})
    def show_grade_target(course_id: PositiveID, gradescope_course_id: GradescopeID | None = None,
                       grading_plan: GradingPlan | None = None, target: Percent = 90) -> Annotated[CallToolResult, GradeTargetView]:
        """Show a separate interactive bar calculator for target-grade and what-if requests.

        Use show_gradebook for a grade grid; do not render this calculator for a plain grades request.

        Resolve the course with list_courses. Read get_grades and read_grading_policy
        before building grading_plan. The tool re-reads both sites; report automatic
        course matches, especially a different term, and request sign-in when needed.
        Scores from the sites are shown separately and are never automatically added.

        For a fixed-weight syllabus, pass a plan covering exactly 100% of the FINAL
        course grade, including future work not yet posted. Each work row has a name,
        final-course percentage weight, and optional grade_ref: coursesite:<grade item
        id> or gradescope:<assignment id from its URL>. A missing ref represents future
        work, not a supplied score. Use each real assessment once; choose one source for
        mirrored grades. Do not map category/course totals or ongoing category averages
        as finished assessments. Split category weights only when counts AND weighting
        are documented. Include an exact syllabus passage as evidence and explain the
        mapping in explanation. A matching quote verifies provenance, not interpretation.

        Never invent weights, future assignment counts, scores, or letter-grade cutoffs.
        An unfinished category with unknown assignment counts may be an ungraded row
        named 'Homework (final category average)' with its full syllabus weight. Do not
        apply an in-progress average as its final score. Explain this in assumptions.
        A base-grade scenario may exclude discretionary bonuses or penalties only when
        that exclusion is explicitly shown in assumptions. Otherwise, if variable weights,
        curves, dropped scores, replacements, or missing policy details cannot be expressed
        by these fixed weights, omit the plan and explain why in chat. The calculator shows the policy limitation. An unavailable score
        is an unknown, not zero. A default 90% target is an editable scenario, not an A
        cutoff. Scenarios assume ungraded work can earn 0–100%; they are not guaranteed
        final grades or submission status. All controls are local; nothing is saved.
        """
        try:
            view = get_grade_target(get_client(), read_grades, course_id, gradescope_course_id, grading_plan, target)
        except MoodleError as exc:
            raise ValueError(str(exc)) from None
        except (ValidationError, TypeError, KeyError, AttributeError):
            raise ValueError('Grade data was incomplete or unexpected. Re-read the grades or open the source.') from None
        summary = f'{view.course_name}: ' + ('Fixed-weight syllabus scenario; estimates are not official final grades.'
                                             if view.projection else view.projection_notice or '')
        return CallToolResult(content=[TextContent(type='text', text=summary)],
                              structuredContent=view.model_dump(mode='json'))
