/** Validate host data and copy only the display fields this feature needs. */
export function readCoursesResult(result, schemaVersion = "courses.v1") {
  const fail = () => { throw new Error("Invalid courses result"); };
  const text = (value, max = 240) => typeof value === "string" && value.trim().length > 0 && value.length <= max;
  const id = (value) => Number.isSafeInteger(value) && value > 0;
  const date = (value) => typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
  const timestamp = (value) => typeof value === "string" && /T.*(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value));
  if (!result || result.schema_version !== schemaVersion || !date(result.week_start) || !text(result.timezone, 80) ||
      !text(result.site_url, 2048) || !Array.isArray(result.courses) || result.courses.length > 12) fail();
  new Intl.DateTimeFormat("en-US", { timeZone: result.timezone });
  const site = new URL(result.site_url);
  if (site.protocol !== "https:" || site.username || site.password || site.search || site.hash) fail();
  const seen = new Set();
  const courses = result.courses.map((course) => {
    if (!course || !id(course.id) || seen.has(course.id) || !text(course.name) || !text(course.code) ||
        course.url !== `${result.site_url}/course/view.php?id=${course.id}` ||
        !["ready", "partial", "unavailable"].includes(course.status) ||
        !Array.isArray(course.assignments) || course.assignments.length > 100 ||
        !Number.isSafeInteger(course.undated_count) || course.undated_count < 0 ||
        !Array.isArray(course.warnings) || course.warnings.length > 8 || course.warnings.some((s) => !text(s, 500))) fail();
    seen.add(course.id);
    const assignmentIds = new Set();
    const assignments = course.assignments.map((item) => {
      const prefix = `${result.site_url}/mod/assign/view.php?id=`;
      if (!item || !id(item.id) || assignmentIds.has(item.id) || !text(item.name) || !timestamp(item.due_at) ||
          !["course", "extension", "unverified"].includes(item.due_basis) || !text(item.url, 2048) ||
          !item.url.startsWith(prefix) || !/^[1-9]\d*$/.test(item.url.slice(prefix.length))) fail();
      assignmentIds.add(item.id);
      return { id: item.id, name: item.name, url: item.url, due_at: item.due_at, due_basis: item.due_basis };
    });
    return { id: course.id, name: course.name, code: course.code, url: course.url,
      status: course.status, assignments, undated_count: course.undated_count, warnings: [...course.warnings] };
  });
  return { courses, week_start: result.week_start, timezone: result.timezone };
}
