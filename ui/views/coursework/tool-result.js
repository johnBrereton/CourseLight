import { readCoursesResult } from "../courses/tool-result.js";

export function readCourseworkResult(result) {
  const view = readCoursesResult(result, "coursework.v1");
  const fail = () => { throw new Error("Invalid coursework result"); };
  const text = (value, max = 240) => typeof value === "string" && value.trim().length > 0 && value.length <= max;
  const timestamp = (value) => typeof value === "string" && /T.*(?:Z|[+-]\d\d:\d\d)$/.test(value) && Number.isFinite(Date.parse(value));
  const kinds = ["resource", "url", "page", "folder", "label", "forum", "lti", "book"];
  const courses = view.courses.map((course, index) => {
    const candidates = result.courses[index].other_work;
    if (!Array.isArray(candidates) || candidates.length > 20) fail();
    const seen = new Set();
    const other_work = candidates.map((item) => {
      if (!item || !Number.isSafeInteger(item.id) || item.id <= 0 || seen.has(item.id) ||
          !text(item.name) || !kinds.includes(item.kind) || !text(item.section) ||
          typeof item.excerpt !== "string" || item.excerpt.length > 500 ||
          !["name", "section", "description"].includes(item.matched_by) ||
          (item.due_at !== null && !timestamp(item.due_at))) fail();
      const expected = item.kind === "label" ? course.url
        : `${result.site_url}/mod/${item.kind}/view.php?id=${item.id}`;
      if (item.url !== expected) fail();
      seen.add(item.id);
      return { id: item.id, name: item.name, url: item.url, kind: item.kind,
        section: item.section, excerpt: item.excerpt, due_at: item.due_at };
    });
    return { ...course, other_work };
  });
  return { ...view, courses };
}
