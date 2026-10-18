export const WEEKDAYS = [
  { code: "M", label: "Mon", name: "Monday" }, { code: "T", label: "Tue", name: "Tuesday" },
  { code: "W", label: "Wed", name: "Wednesday" }, { code: "R", label: "Thu", name: "Thursday" },
  { code: "F", label: "Fri", name: "Friday" },
];
const dayNames = { M: "Mon", T: "Tue", W: "Wed", R: "Thu", F: "Fri", S: "Sat", U: "Sun" };

export function clock(minutes) {
  const hour = Math.floor(minutes / 60) % 24;
  return `${hour % 12 || 12}:${String(minutes % 60).padStart(2, "0")} ${hour < 12 ? "AM" : "PM"}`;
}

export function daysLabel(days) {
  return [...days].map((day) => dayNames[day]).join(" · ") || "Days TBA";
}

export function dateSpecific(meeting) {
  return meeting.start_date && meeting.end_date &&
    (Date.parse(meeting.end_date) - Date.parse(meeting.start_date)) / 86400000 < 7;
}

export function dateLabel(value) {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" })
    .format(new Date(`${value}T12:00:00Z`));
}

export function recurringEntries(sections) {
  return sections.flatMap((section) => section.meetings.flatMap((meeting, index) =>
    !dateSpecific(meeting) && meeting.start_minute !== null
      ? WEEKDAYS.filter((day) => meeting.days.includes(day.code)).map((day) =>
        ({ section, meeting, day: day.code, key: `${section.crn}-${index}-${day.code}` })) : []));
}

export function placeDay(entries) {
  const sorted = [...entries].sort((a, b) => a.meeting.start_minute - b.meeting.start_minute ||
    a.meeting.end_minute - b.meeting.end_minute || a.key.localeCompare(b.key));
  let group = [], ends = [], until = 0;
  const placed = [];
  function flush() {
    placed.push(...group.map((item) => ({ ...item, columns: ends.length })));
    group = []; ends = []; until = 0;
  }
  for (const entry of sorted) {
    if (group.length && entry.meeting.start_minute >= until) flush();
    let column = ends.findIndex((end) => end <= entry.meeting.start_minute);
    if (column < 0) column = ends.length;
    ends[column] = entry.meeting.end_minute;
    until = Math.max(until, entry.meeting.end_minute);
    group.push({ ...entry, column });
  }
  flush();
  return placed;
}
