import assignmentIcon from "../../shared/assets/icons/file-earmark-arrow-up.svg";

export function AssignmentRow({ assignment, timezone }) {
  const due = new Intl.DateTimeFormat("en-US", {
    weekday: "long", month: "long", day: "numeric", hour: "numeric", minute: "2-digit",
    timeZone: timezone, timeZoneName: "short",
  }).format(new Date(assignment.due_at));
  return (
    <li className="assignment-row">
      <img className="assignment-icon" src={assignmentIcon} alt="" aria-hidden="true" />
      <div className="assignment-info">
        <a href={assignment.url} target="_blank" rel="noopener noreferrer">{assignment.name}</a>
        <p><strong>Due:</strong> <time dateTime={assignment.due_at}>{due}</time></p>
        {assignment.due_basis === "extension" && <span className="deadline-note">Your extension is included</span>}
      </div>
    </li>
  );
}
