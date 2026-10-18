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
    schedule/                     One React view for both schedule tools
  shared/
    bridge.js                     MCP Apps host messaging
    components/                   Glass surfaces, CourseLight mark, and header
    schedule/                     Reusable weekly grid, layout, and class details
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
