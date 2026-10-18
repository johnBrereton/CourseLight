import sourceIcon from "../../shared/assets/icons/arrow-up-right.svg";

const kinds = {
  resource: "File", url: "Link", page: "Page", folder: "Folder",
  label: "Course post", forum: "Forum overview", lti: "External activity", book: "Book",
};

export function CourseworkRow({ item, timezone }) {
  const due = item.due_at && new Intl.DateTimeFormat("en-US", {
    weekday: "long", month: "long", day: "numeric", hour: "numeric", minute: "2-digit",
    timeZone: timezone, timeZoneName: "short",
  }).format(new Date(item.due_at));
  return (
    <li className="assignment-row">
      <img className="assignment-icon" src={sourceIcon} alt="" aria-hidden="true" />
      <div className="assignment-info">
        <a href={item.url} target="_blank" rel="noopener noreferrer">{item.name}</a>
        <span className="deadline-note">{kinds[item.kind]} · {item.section}</span>
        {due ? <p><strong>Posted due date:</strong> <time dateTime={item.due_at}>{due}</time></p>
          : <p>Due date not provided · week unverified</p>}
        {item.excerpt && <p>{item.excerpt}</p>}
      </div>
    </li>
  );
}
