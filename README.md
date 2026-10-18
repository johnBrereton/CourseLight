# CourseLight

A small, read-only MCP server for Moodle, including Lehigh CourseSite. Connect
your own account to an MCP client to look up courses, plan deadlines, understand
assignment requirements, read Moodle Pages, and review your released grades.



## Read tools

| Tool | Purpose |
| --- | --- |
| `get_profile` | Confirm the connected account and available read functions |
| `list_courses` | List your enrolled courses and their Moodle links |
| `get_course_contents` | Browse sections, activity descriptions, and resource links |
| `list_assignments` | Read one course's assignment requirements and dates |
| `get_assignment_status` | Read one assignment's requirements and your submission status |
| `get_grades` | Read grades released to you for a course |
| `get_upcoming_work` | Read upcoming action events in a time interval, with pagination |
| `read_page` | Read the text of a Moodle Page, with pagination |
| `login` | Lehigh only: open a browser to sign in with SSO and Duo for CourseSite, Banner, and Degree Works |

At Lehigh, these read the registrar's systems through the same sign-in:

## Registration tools
| Tool | Purpose |
| --- | --- |
| `list_terms` | List Banner term codes, e.g. `202640` for Fall 2026 (no sign-in) |
| `search_classes` | Search or browse the class schedule by subject, number or number range, attribute (HU, SS, W, ...), or keyword: CRNs, times, rooms, instructors, seats, waitlists (no sign-in) |
| `get_course_description` | Read a section's catalog description (no sign-in) |
| `build_schedules` | Build conflict-free schedules from candidate courses, pairing lectures with their labs, with filters for open seats, times, days off, and credits (no sign-in) |
| `get_my_registration` | Read your registered classes for a term; past terms include grades |
| `get_degree_audit` | Read your Degree Works audit: progress, advisors, met and unmet requirements |
| `get_gpa` | Read cumulative and major GPA, credits, and GPA by term |
| `get_course_history` | List every course on your record with term, grade, and credits |

Off campus, Degree Works needs the Lehigh VPN. A Degree Works audit doesn't replace advising.

## Visualized tools

Visualized tools display interactive components inline in an MCP Apps-compatible
host. They return validated `structuredContent` and a short text fallback.

| Tool | Purpose |
| --- | --- |
| `show_courses` | Show courses and weekly assignment deadlines |
| `show_deadlines` | Show weekly assignment deadlines in a chronological timeline |
| `show_coursework` | Explicit “coursework” / “course work” requests: add a riskier search for possible work in other course posts |
| `show_class_schedule` | Show registered Banner classes in a Monday–Friday grid |
| `show_schedule_options` | Compare potential schedules using the same grid |

Ordinary assignment requests use `show_courses`. The broader tool uses keyword
clues and may include unrelated or older items, or miss work. Its cards label
that limitation and mark undated candidates as week-unverified.

The schedule views show recurring class times in America/New_York. Date-specific
meetings, weekend classes, and unknown times remain in the tool result for chat
and class details; they are not plotted in the weekday grid. Proposed
schedules can be switched locally; nothing is registered, dropped, or saved.

Python tools live in `visualizations/<name>/`; their React views live in
`ui/views/<name>/`. Reusable UI code is in `ui/shared/`, and generated
bundles are in `ui/dist/`. See the [folder guide and adding a visualization](visualizations/README.md)
for the Courses example and its coverage limits.

## Setup

You need Python 3.10 or newer and your own Moodle web-service token. Your
institution must enable Moodle web services and allow the functions listed below.
CourseLight cannot enable them or create a token for you. If your institution does
not offer a token, ask its Moodle administrator about permitted access.

```sh
git clone https://github.com/johnBrereton/CourseLight.git
cd CourseLight
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`: replace `MOODLE_URL` with your institution's HTTPS Moodle base URL
and set `MOODLE_TOKEN` to your own token. For Lehigh, the base URL is
`https://coursesite.lehigh.edu`. Do not include `/login/index.php` or
`/webservice/rest/server.php`. Moodle installed in a subdirectory is supported,
for example `https://example.edu/moodle`.

### Connect an MCP client

Use a client that supports local **stdio** MCP servers. Add the following server
configuration, replacing both paths with the absolute paths on your machine:

```json
{
  "mcpServers": {
    "courselight": {
      "command": "/absolute/path/to/CourseLight/.venv/bin/python",
      "args": ["/absolute/path/to/CourseLight/server.py"]
    }
  }
}
```

The same example is in `mcp.json.example`. Your client determines where to put
this configuration. On Windows, use `python.exe` under `.venv\Scripts` and escape
backslashes in JSON, or use forward slashes. The client starts the server when
needed. The default stdio connection starts no web server or public endpoint.
The server reads `.env` beside its source files regardless of the client's
working directory;
existing environment variables take precedence. Restart the connection after
changing credentials or updating the tool definitions.

Start with “List my courses,” then “Show the assignments and upcoming deadlines
for this course.” You can also ask “Explain this Moodle Page and link to the
source” or “Show my released grades.” Use the tools for study support and planning
in accordance with your instructor's rules.

## Privacy and boundaries

Each person runs their own copy with their own account. Share the repository,
never a configured connection or a filled-in `.env` file. Anyone who can invoke
your connection can read the course information available to that account.
Course information returned by the tools is sent to your MCP client and may be
processed or retained according to that client's settings.

CourseLight's transport enforces a fixed allowlist of read functions. These
requests use POST because that is how Moodle's REST API works; they do not invoke
submission or assessment-write functions. A token may have broader permissions
outside this application. Where possible, ask for a service token restricted to
the required reads. Credentials travel only to the configured HTTPS Moodle URL;
redirects are not followed. Token fields and debug traces are stripped from tool
results, and transport errors do not expose raw server responses. The Lehigh
session cookies are used only by a local headless browser on Lehigh's SSO,
Banner, and Degree Works sites, and are never returned in tool results.

There are no local journals, staged submissions, or downloaded course files. The
only application data is the Lehigh sign-in session in `~/.lehigh-mcp/`, outside
the repository. `.env`, virtual environments, local MCP configuration,
and logs are ignored by Git. The default stdio connection needs no tunnel key,
hosting account, database, or public listener.

## Data limitations

- A calendar is not an exhaustive list of work. Combine upcoming events with
  assignments and actual submission status.
- A missing grade is not a zero; a missing deadline or calendar event is not proof
  that work is complete. A draft is not a final submission.
- Course and assignment access depend on Moodle permissions and availability.
  `get_profile` reports advertised API functions, not access to every activity.
- `get_upcoming_work` takes Unix timestamps in seconds. Keep the same time range
  and pass `next_after_event_id` as `after_event_id` until it is `null`.
- For `read_page`, use a page module's `instance` from `get_course_contents` as
  `page_id`. Follow `next_offset` using the same page until it is `null`.
  Images, embedded documents, layout, and diagrams are omitted; check the original.
- Each response is capped at 20 MiB. Moodle reads use a 30-second request timeout
  and at most three attempts for temporary network or service failures.

The read tools return `{ "ok": true, "fetched_at": ..., "data": ... }` or
`{ "ok": false, "error": { "code": ..., "message": ... } }`.
Warnings and unavailable data should be reported, rather than interpreted as
completion or missing coursework. Always verify consequential dates and grades
against the linked source in Moodle.

## Required Moodle functions

`moodle.py` contains the full allowlist:

```text
core_webservice_get_site_info
core_enrol_get_users_courses
core_course_get_contents
mod_assign_get_assignments
mod_assign_get_submission_status
gradereport_user_get_grade_items
core_calendar_get_action_events_by_timesort
core_calendar_get_action_events_by_course
mod_page_get_pages_by_courses
```

If `get_profile` reports a function unavailable, that tool needs your institution's
administrator to enable the corresponding read in the service. A Moodle error
may also mean an expired token, a role restriction, or an unavailable activity.
Share the tool name and error code when asking for help, never your token, grades,
private course content, or a token-bearing URL.
