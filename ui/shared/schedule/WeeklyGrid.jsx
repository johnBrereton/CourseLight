import { useId } from "react";
import { GlassSurface } from "../components/GlassSurface.jsx";
import { WEEKDAYS, clock, recurringEntries, placeDay } from "./layout.js";
import "./schedule-grid.css";

export function WeeklyGrid({ sections, onSelect }) {
  const labelId = useId();
  const entries = recurringEntries(sections);
  const courses = [...new Set(sections.map((section) => section.course))].sort();
  const first = Math.floor(Math.min(540, ...entries.map((entry) => entry.meeting.start_minute)) / 60) * 60;
  const last = Math.ceil(Math.max(1020, ...entries.map((entry) => entry.meeting.end_minute)) / 60) * 60;
  const hours = Array.from({ length: (last - first) / 60 + 1 }, (_, index) => first + index * 60);
  const shortestMeeting = Math.min(75, ...entries.map(({ meeting }) => meeting.end_minute - meeting.start_minute));
  const minuteHeight = Math.max(1.3, 90 / Math.max(30, shortestMeeting));
  return (
    <>
      <span id={labelId} className="schedule-sr-only">Weekly class schedule, Monday through Friday, New York time</span>
      <div className="schedule-grid-scroll" role="region" aria-labelledby={labelId} tabIndex={0}>
        <div className="schedule-surface">
          <GlassSurface className="schedule-material" aria-hidden="true" />
          <div className="week-grid" style={{ "--grid-height": `${(last - first) * minuteHeight}px`, "--hour-height": `${60 * minuteHeight}px` }}>
            <div className="week-corner" aria-hidden="true" />
            {WEEKDAYS.map((day) => <div className="week-heading" key={day.code}>{day.label}</div>)}
            <div className="week-times" aria-hidden="true">
              {hours.map((minute) => <span key={minute} style={{ top: (minute - first) * minuteHeight }}>{clock(minute)}</span>)}
            </div>
            {WEEKDAYS.map((day) => {
              const blocks = placeDay(entries.filter((entry) => entry.day === day.code));
              return <section key={day.code} className="week-day" aria-label={day.name}>
                {!blocks.length && <span className="day-free">—</span>}
                {blocks.map(({ section, meeting, key, column, columns }) => (
                  <button key={key} type="button" className={`class-block course-tone-${courses.indexOf(section.course) % 5}`}
                    style={{ top: (meeting.start_minute - first) * minuteHeight + 2,
                      height: Math.max(8, (meeting.end_minute - meeting.start_minute) * minuteHeight - 4),
                      left: `calc(${column / columns * 100}% + 3px)`, width: `calc(${100 / columns}% - 6px)` }}
                    title={`${section.course} · ${section.title}\n${clock(meeting.start_minute)}–${clock(meeting.end_minute)}\n${section.instructors.join(" · ") || "Professor TBA"}\n${meeting.location}`}
                    aria-label={`${day.name}, ${section.course}, ${section.title}, ${section.kind}, ${clock(meeting.start_minute)} to ${clock(meeting.end_minute)}, ${section.instructors.join(" and ") || "Professor TBA"}, ${meeting.location}. Show details.`}
                    onClick={() => onSelect(section)}>
                    <strong className="class-block-header">{section.course}</strong>
                    <span className="class-time">{clock(meeting.start_minute).replace(" AM", "a").replace(" PM", "p")}{section.kind && ` · ${section.kind}`}</span>
                    <span className="class-professor">{section.instructors.length ? section.instructors.map((name) => {
                      const parts = name.split(",");
                      return parts.length === 2 ? `${parts[1].trim()} ${parts[0].trim()}` : name;
                    }).join(" · ") : "Professor TBA"}</span>
                    <span className="class-location">{meeting.location.replace(/^\d{3}\s+/, "")}</span>
                  </button>
                ))}
              </section>;
            })}
          </div>
        </div>
      </div>
    </>
  );
}
