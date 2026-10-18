import { useEffect, useId, useRef } from "react";
import { dateLabel, daysLabel } from "./layout.js";

export function ClassDetails({ section, onClose, proposed }) {
  const ref = useRef(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog ref={ref} className="class-details" aria-labelledby={titleId} onClose={onClose}>
      <div className="details-topline">
        <span>{section.course} · {section.kind || "Class"}</span>
        <button type="button" className="details-close" aria-label="Close class details" onClick={onClose}>×</button>
      </div>
      <h2 id={titleId}>{section.title}</h2>
      <p className="details-subtitle">Section {section.section || "—"} · CRN {section.crn}
        {section.credits !== null && ` · ${section.credits} credits`}</p>
      {!!section.instructors.length && <p>{section.instructors.join(" · ")}</p>}
      <ul className="details-meetings">
        {section.meetings.map((meeting, index) => <li key={index}>
          <strong>{daysLabel(meeting.days)} · {meeting.time_label}</strong>
          <span>{meeting.location}</span>
          {meeting.kind && <span>{meeting.kind}</span>}
          {meeting.start_date && meeting.end_date && <span>
            {dateLabel(meeting.start_date)}{meeting.end_date !== meeting.start_date && ` – ${dateLabel(meeting.end_date)}`}
          </span>}
        </li>)}
      </ul>
      {!section.meetings.length && <p>No meeting time was provided.</p>}
      {proposed && section.seats_available !== null && <p className="details-seat">
        {section.seats_available > 0 ? `${section.seats_available} seats available when fetched` : "No open seats when fetched"}
      </p>}
      {!proposed && section.registration_status && <p className="details-seat">{section.registration_status}</p>}
    </dialog>
  );
}
