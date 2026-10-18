import { GlassSurface } from "../../shared/components/GlassSurface.jsx";
import arrow from "../../shared/assets/icons/arrow-up-right.svg";

export function DeadlineTimeline({ view }) {
  const options = { timeZone: view.timezone };
  const dayFormat = new Intl.DateTimeFormat("en-US", { ...options, year: "numeric", month: "long", day: "numeric" });
  const weekdayFormat = new Intl.DateTimeFormat("en-US", { ...options, weekday: "short" });
  const dateFormat = new Intl.DateTimeFormat("en-US", { ...options, month: "short", day: "numeric" });
  const timeFormat = new Intl.DateTimeFormat("en-US", { ...options, hour: "numeric", minute: "2-digit" });
  const deadlines = view.courses.flatMap((course) => course.assignments.map((assignment) => ({ course, assignment })))
    .sort((a, b) => Date.parse(a.assignment.due_at) - Date.parse(b.assignment.due_at) ||
      a.course.name.localeCompare(b.course.name) || a.assignment.name.localeCompare(b.assignment.name));
  const groups = new Map();
  for (const item of deadlines) {
    const key = dayFormat.format(new Date(item.assignment.due_at));
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(item);
  }
  const unavailable = view.courses.filter((course) => course.status === "unavailable");
  return <>
    {deadlines.length ? <ol className="deadline-timeline" aria-label="Deadlines by date">
      {[...groups].map(([day, items]) => {
        const first = items[0].assignment.due_at;
        return <li className="timeline-day" key={day}>
          <h2 className="timeline-date"><time dateTime={first} title={day}>
            <span>{weekdayFormat.format(new Date(first))}</span>
            <strong>{dateFormat.format(new Date(first))}</strong>
          </time></h2>
          <ol className="timeline-items" aria-label={day}>
            {items.map(({ course, assignment }) => <li key={`${course.id}-${assignment.id}`} className="deadline-card">
              <GlassSurface className="deadline-material" aria-hidden="true" />
              <a className="deadline-link" href={assignment.url} target="_blank" rel="noopener noreferrer">
                <span className="deadline-meta"><span className="deadline-course">{course.name}</span>
                  <time dateTime={assignment.due_at}>{timeFormat.format(new Date(assignment.due_at))}</time>
                </span>
                <span className="deadline-name">{assignment.name}<img src={arrow} alt="" aria-hidden="true" /></span>
                {assignment.due_basis === "extension" && <span className="deadline-extension">Extended deadline</span>}
              </a>
            </li>)}
          </ol>
        </li>;
      })}
    </ol> : <p className="timeline-message">No assignment deadlines returned for this week. Check CourseSite for other work.</p>}
    {unavailable.length > 0 && <p className="timeline-unavailable" role="note">Couldn’t load assignments for {unavailable.map((course) => course.name).join(", ")}.</p>}
  </>;
}
