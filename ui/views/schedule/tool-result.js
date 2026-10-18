export function readScheduleResult(result) {
  const fail = () => { throw new Error("Invalid schedule result"); };
  const text = (value, max = 240, empty = false) => typeof value === "string" && (empty || value.trim().length > 0) && value.length <= max;
  const array = (value, max) => Array.isArray(value) && value.length <= max;
  const credits = (value) => value === null || typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 60;
  const date = (value) => value === null || typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
  if (!result || result.schema_version !== "schedule.v1" || !["registered", "proposed"].includes(result.mode) ||
      typeof result.term !== "string" || !/^\d{6}$/.test(result.term) || !text(result.term_label) || result.timezone !== "America/New_York" ||
      !array(result.options, 10) || !array(result.notices, 16) || result.notices.some((note) => !text(note, 500))) fail();
  if (result.mode === "registered" && result.options.length !== 1) fail();
  const optionIds = new Set();
  const options = result.options.map((option) => {
    if (!option || typeof option.id !== "string" || !/^[a-z0-9-]{1,40}$/.test(option.id) || optionIds.has(option.id) ||
        !text(option.label) || !credits(option.total_credits) || !array(option.sections, 40)) fail();
    optionIds.add(option.id);
    const crns = new Set();
    const sections = option.sections.map((section) => {
      if (!section || typeof section.crn !== "string" || !/^\d{5}$/.test(section.crn) || crns.has(section.crn) ||
          !text(section.course) || !text(section.title) || !text(section.section, 20, true) ||
          !text(section.kind, 100, true) || !credits(section.credits) || !text(section.registration_status, 120, true) ||
          !array(section.instructors, 20) || section.instructors.some((name) => !text(name)) ||
          !array(section.meetings, 40) || section.seats_available !== null && !Number.isSafeInteger(section.seats_available)) fail();
      crns.add(section.crn);
      const meetings = section.meetings.map((meeting) => {
        if (!meeting || typeof meeting.days !== "string" || !/^[MTWRFSU]{0,7}$/.test(meeting.days) ||
            new Set(meeting.days).size !== meeting.days.length || !text(meeting.time_label, 80) ||
            !text(meeting.location) || !text(meeting.kind, 100, true) || !date(meeting.start_date) || !date(meeting.end_date)) fail();
        const { start_minute: start, end_minute: end } = meeting;
        if (!(start === null && end === null) &&
            !(Number.isSafeInteger(start) && Number.isSafeInteger(end) && start >= 0 && start < end && end <= 1440)) fail();
        if (meeting.start_date && meeting.end_date && meeting.start_date > meeting.end_date) fail();
        return { days: meeting.days, start_minute: start, end_minute: end, time_label: meeting.time_label,
          location: meeting.location, kind: meeting.kind, start_date: meeting.start_date, end_date: meeting.end_date };
      });
      return { crn: section.crn, course: section.course, section: section.section, title: section.title,
        kind: section.kind, credits: section.credits, registration_status: section.registration_status,
        instructors: [...section.instructors], meetings, seats_available: section.seats_available };
    });
    return { id: option.id, label: option.label, total_credits: option.total_credits, sections };
  });
  return { mode: result.mode, term: result.term, term_label: result.term_label, options, notices: [...result.notices] };
}
