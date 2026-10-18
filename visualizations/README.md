# Visualized tools

Each visualization has a Python feature folder and a matching React view folder.
Use the same name in both places, such as `courses`.

```text
server.py                         Calls register_visualizations once
visualizations/
  __init__.py                     Registers each visualized tool
  resources.py                    Packages HTML, React, CSS, and the host bridge
  courses/
    __init__.py                   Exports register_courses
    resource.py                   MCP tool, resource URI, and result metadata
    service.py                    Fetches and prepares CourseSite data
    models.py                     Validates request and response data
  coursework/
    __init__.py                   Exports register_coursework
    resource.py                   Separate opt-in tool and UI resource
    service.py                    Adds discovery to the assignment reader
    discovery.py                  Finds possible work in other course posts
    models.py                     Extends the result with heuristic candidates
  materials/
    resource.py                   Exam-prep material selection tool
    service.py                    Reads real modules and browser file links
    models.py                     Topic selections and material groups
  gradebook/
    resource.py                   Gradebook tool and syllabus reader
    service.py                    Adapts the shared two-site grade reader
    syllabus.py                   Visible syllabus sources and bounded extraction
    models.py                     Source grade rows
  grade_target/
    resource.py                   Separate grade-target tool and resource
    service.py                    Verifies syllabus evidence and grade references
    models.py                     Fixed-weight scenario inputs and result
  degree_progress/
    resource.py                   Degree-completion ring and GPA tool
    service.py                    Reuses the existing Degree Works audit reader
    models.py                     Reported progress, GPA, and audit date
  deadlines/
    resource.py                   Timeline tool; reuses Courses models and reader
  schedule/
    resource.py                   Registered and proposed schedule tools
    service.py                    Adapts the existing Banner readers
    models.py                     One shared schedule result contract
ui/
  views/
    courses/                      React components, CSS, HTML, and result adapter
      main.jsx                    React entry point
    coursework/                   Broader view, candidate rows, and risk notice
    deadlines/                    Simple timeline, grouped by local due date
    materials/                    Expandable topic bars and download links
    degree_progress/              Degree/major completion rings and GPA card
    gradebook/                    Compact source grade grid
    grade_target/                 Draggable score bars and projected final grade
    schedule/                     One React view for both schedule tools
  shared/
    bridge.js                     MCP Apps host messaging
    components/                   Glass surfaces, CourseLight mark, and header
    schedule/                     Reusable weekly grid, layout, and class details
    grades/                       Shared grade shell, formatting, and result validation
    styles/                       Common theme tokens and branding styles
    assets/                       Logos, icons, and licenses
  dist/
    courses/                      Generated bundle.js and bundle.css
    coursework/                   Separate generated coursework bundle
    schedule/                     Shared registered/proposed schedule bundle
  build.mjs                       Builds every folder under views/
  package.json                    Shared frontend dependencies
```

## Adding a visualization

1. Add `visualizations/<name>/` with its `models.py`, `service.py`, and `resource.py`.
   Export its registration function from that folder's `__init__.py`.
2. Add `ui/views/<name>/` with `main.jsx`, `index.html`, components, and CSS.
   Import shared pieces from `ui/shared/`; keep feature-specific code in the view.
3. Give the tool its own `ui://courselight/<name>/v1.html` resource URI.
   In its resource callback, return `component_html('<name>')` from
   `visualizations.resources`. Follow the Courses HTML template's bundle and
   bridge tags, which that helper inlines.
4. Register the tool in `visualizations/__init__.py`. `server.py` needs no changes.
5. Run `npm --prefix ui run build:ui`. New view folders are discovered automatically.
   Include the generated `ui/dist/<name>/` assets with the source so Python can
   serve the component without a Node server.

An MCP resource URI identifies the HTML returned by Python; it is not a file
path or a public URL. Folder moves do not change the existing Courses URI.
React receives the tool's `structuredContent` through the shared host bridge.

Keep Moodle reads within `moodle.py`'s allowlist, sanitize course content, and
keep credentials and local tunnel configuration outside the feature folders.

## Two tool paths

| User request | Tool | Resource / result schema |
| --- | --- | --- |
| “Show my courses” or “weekly assignments” | `show_courses` | `ui://courselight/courses/v1.html` / `courses.v1` |
| Explicit “coursework” or “course work” | `show_coursework` | `ui://courselight/coursework/v1.html` / `coursework.v1` |

Both descriptions tell the assistant to use the broader tool only for explicit
coursework requests, never as an automatic fallback when assignments are empty.
This is tool-selection guidance: an MCP server receives tool arguments, not the
user's original chat, so it cannot enforce a literal keyword gate. The code does
enforce isolation: `show_courses` never calls coursework discovery.

`show_courses` reads assignment deadlines and checks personal extensions where
available. It does not search other posts. `show_coursework` reuses that reader
and adds possible matches in `other_work`. Its React view reuses the Courses app
and card components, adding candidate rows and a visible risk notice; the ordinary
Courses bundle does not include the coursework renderer. “Due” counts refer only
to returned assignment deadlines; candidates appear as “to check.”

## Broader coursework coverage

This is a **riskier, keyword-based search**: it can include unrelated or older
items and miss real coursework. It is not an AI classification or a complete
weekly checklist. Verify candidates in CourseSite.

`coursework/discovery.py` uses the existing `core_course_get_contents` read and,
when a Moodle Page is present, `mod_page_get_pages_by_courses`. It searches visible
titles, section names, descriptions, and up to 20,000 characters of Page text
for homework, problem sets, projects, readings, and similar clues. Common answer
keys, solutions, lecture slides, recordings, policy notices, and syllabus titles are excluded.

Only explicit Moodle due-date metadata establishes a date. Dated candidates
must fall in the selected week. Undated candidates are shown separately as
week-unverified, never counted as due, and capped at 20 per course. Each item
includes its source link and section. File contents, external tools, and forum
discussion replies are not fetched, and quiz attempts/questions remain excluded.
The Moodle API allowlist is unchanged. An assignment read can fail while the
same card still shows discoverable coursework with a loading-failure notice.

The module metadata and date fields follow the
[Moodle course contents API](https://github.com/moodle/moodle/blob/MOODLE_405_STABLE/course/externallib.php).

## Class schedules

`show_class_schedule(term)` reads actual registrations with
`lehigh.get_registration`. It requires the existing Lehigh sign-in and never
guesses registered sections from CourseSite names. Dropped, withdrawn, cancelled,
and waitlisted records are excluded from the class grid.

`show_schedule_options(term, courses, ...)` reuses `lehigh.build_schedules`,
including its linked lecture/lab pairing and preference filters. Switching
returned options is local React state. No schedule or registration is written.
Prerequisites, holds, and restrictions are not checked by that existing builder.

Both tools return `schedule.v1` and point to `ui://courselight/schedule/v1.html`.
The shared `ui/shared/schedule/WeeklyGrid.jsx` accepts normalized sections;
`layout.js` positions overlapping blocks in separate lanes. `ClassDetails.jsx`
provides keyboard-accessible meeting details. Shared branding and theme styles
are used by the course cards and the schedule view.

This is a weekly pattern in New York time, not a holiday-aware calendar. Meetings
whose date ranges are shorter than one week (including one-off exams), weekend
meetings, and TBA times remain in the result for chat and class details. They are
not plotted in the weekday grid; unknown times are never placed at a guessed hour. Narrow hosts can scroll the five-day grid
horizontally. Course details retain the original meeting dates and source CRNs.

## Deadline timeline

`show_deadlines(course_ids, timezone, week_start)` displays assignment deadlines
in chronological order, grouped by local calendar date, with CourseSite links.
It reuses `courses.get_courses`, `CoursesQuery`, and `CoursesView` (`courses.v1`),
so there is no second assignment fetcher or duplicate deadline schema. Its
resource is `ui://courselight/deadlines/v1.html`; React lives in `ui/views/deadlines/`
and reuses the Courses host-result validator, shared bridge, and glass surfaces.

Coverage is assignment-only. Unknown dates are not placed on the timeline, and
submission/completion status is not inferred. The assistant states the selected
week, timezone, and coverage in chat. The view handles no returned deadlines,
failed loads, and courses that could not be read.


## Study materials

`show_study_materials(course_id, groups)` renders `ui://courselight/materials/v1.html`
with the `materials.v1` schema. First inspect `get_course_contents`, then select
actual `module.id` values in groups such as `{"title": "Type systems", "module_ids": [...]}`.
Usually three topic groups keep exam-prep requests focused. Establish the exam
scope from the user or a posted review outline; otherwise describe the selection
as suggested study materials in chat. This tool does not infer an exam syllabus.

The service re-reads the selected modules and returns only accessible resources,
folders, pages, URLs, and books. Quizzes and submissions are excluded. File rows
have Download links; other resources open their CourseSite source. Download URLs
use Moodle's browser `pluginfile.php` endpoint and `forcedownload=1`, with no web
service token. A CourseSite browser sign-in is required. See [Moodle file handling](https://moodledev.io/docs/4.5/apis/subsystems/external/files).
The study-materials tool does not fetch, cache, or bundle file contents, and there is no ZIP or
"download all" action. All expansion state is local to the React view.


## Gradebook

`show_gradebook(course_id, gradescope_course_id?)` renders
`ui://courselight/gradebook/v1.html` with `gradebook.v1`. It calls the same guarded
`get_grades` reader as the text tool through an injected callback, retaining both
CourseSite and Gradescope results and their source failures. The source switch is
local state. No combined total is invented: a CourseSite course total is labeled
as reported, and a mirrored Gradescope grade is not automatically added to it.
Unavailable scores remain unknown, including submitted work without a score.
Hidden grades are not displayed; category totals stay separate from assessments.

## Grade target

`show_grade_target(course_id, gradescope_course_id?, grading_plan?, target=90)`
renders the separate `ui://courselight/grade_target/v1.html` resource with
`grade_target.v1`. It reuses the grade reader and adds a syllabus-backed scenario.
Plain grade requests use the grid; target-grade and what-if requests use this tool.
Each remaining assessment or unfinished category becomes a vertical score bar.
Dragging a bar or using its arrow keys updates the projected final grade locally.
Syllabus details and assumptions expand below the chart.

First call `read_grading_policy(course_id)` and `get_grades`.
The syllabus reader discovers visible syllabus/grading-policy modules in the
selected enrolled course. It supports Moodle Pages, one PDF in a syllabus resource,
and public Google Docs linked as syllabi. Other formats or sign-in-protected Docs
return a source link and an unavailable notice. It accepts module IDs, not arbitrary
URLs. The existing Moodle API allowlist is unchanged.

PDF reads use the configured Moodle host's `webservice/pluginfile.php` endpoint,
with no redirects. The token stays server-side. PDF extraction runs in a separate
process with a 15-second timeout, 10 CPU seconds on POSIX, 5 MB file/content limits,
30 pages, and 60,000 characters; Linux also caps address space. Nothing is saved.
Scanned PDFs require manual review. See [Moodle file handling](https://moodledev.io/docs/4.5/apis/subsystems/external/files)
and [pypdf text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).

The assistant interprets the complete syllabus and supplies `grading_plan`:

- `syllabus_module_id`, an exact `evidence` passage, and a brief `explanation`.
- `work`: distinct rows with final-course `weight` percentages summing to 100.
  An optional `grade_ref` uses `coursesite:<grade item id>` or
  `gradescope:<assignment id from its URL>`. Scores are re-read, never supplied.
- `assumptions`: visible conditions, such as excluding discretionary extras or
  treating an unfinished homework category as an adjustable final average.

The server verifies the source passage, weights, and grade references. This
checks provenance and arithmetic structure, **not the assistant's interpretation**
of a syllabus. Never infer missing weights, assignment counts, or letter cutoffs.
Use one source per assessment; totals, stale/excluded scores, and percentages
outside 0–100 cannot be used as released assessment scores in the projection.
A full unfinished category can remain unknown; do not treat its current average
as a final score. Unsupported variable weights, curves, or drop/replacement rules
should leave projections unavailable unless the scenario explicitly excludes an
additive discretionary adjustment and states that condition.

The React calculator uses `secured = sum(weight * released_percent / 100)` and
`needed = (target - secured) / unresolved_weight * 100`. It handles targets already
covered, targets above the possible maximum, and no unresolved work. Required
percentages round upward to a tenth. Per-item sliders answer what is needed on one
item while holding the other estimates fixed. The default 90% target is a scenario,
not a letter grade. Changes are local and reset when a new tool result arrives.


## Degree progress

`show_degree_progress()` renders `ui://courselight/degree_progress/v1.html`
with `degree_progress.v1`. It calls the existing `lehigh.fetch_audit()` reader
once and selects the reported degree-completion percentage, each `MAJOR` block’s
completion percentage, and cumulative GPA from `summarize_audit`. Major progress
is shown separately for each major; it is not calculated or averaged. It does not calculate completion from credits, average
degree programs, run a new audit, or include personal identifiers and advisors.

The compact React card uses matched SVG rings, shared glass surfaces, and the
shared MCP Apps bridge. It shows the audit date and a Degree Works link. Missing
values stay unavailable rather than becoming zero. The assistant also reports
the audit date in chat; an audit snapshot does not establish graduation eligibility.
The same Lehigh sign-in and off-campus VPN requirements apply as to `get_degree_audit`.


## Campus maps and study rooms

`show_course_map(term, on_date=None)` reuses registered Banner meetings and
renders `ui://courselight/course_map/v1.html`. Course chips show or hide building
pins on Apple Maps. It uses verified Lehigh campus coordinates where available,
and conservative Apple building searches otherwise. The card has no timetable
or route calculation.

Set a browser-scoped `APPLE_MAPS_TOKEN` in your ignored `.env`, then restart the
MCP process. Optional `APPLE_MAPS_WIDGET_DOMAIN` selects a dedicated HTTPS origin.
See [Apple Maps setup](maps/README.md) for token restrictions, host CSP requirements,
the fields sent to Apple, and connection verification. The public web token is
delivered only in component metadata, never in model-facing data or built files.

Feature code lives in `course_map/` and `ui/views/course_map/`; shared provider
configuration is in `maps/` and shared React map rendering in `ui/shared/maps/`.

`show_study_rooms(start, end, query=None, min_capacity=0)` uses Evan's 25Live
reader and the same map for a room picker. The card checks availability, presents
an exact review, and submits only after **Reserve room**. App-only tools handle
the review, confirmation, and status checks. `show_study_room(event_id)` reads an
existing booking. See the [room flow](study_rooms/README.md) for the contract and
recovery behavior.
