import { check, text, readCourse } from "../../shared/grades/result.js";

export function readGradebookResult(view) {
  const safeURL = readCourse(view, "gradebook.v1");
  check(Array.isArray(view.sources) && view.sources.length > 0 && view.sources.length <= 2);
  for (const source of view.sources) {
    check(["coursesite", "gradescope"].includes(source.site) && text(source.name) && Array.isArray(source.items) && source.items.length <= 300);
    if (source.url) safeURL(source.url);
    for (const item of source.items) {
      check(/^(coursesite|gradescope):\d+$/.test(item.ref) && text(item.name) && text(item.display_score) && text(item.status) &&
        ["course", "category", "assessment"].includes(item.kind) && (item.percent == null || Number.isFinite(item.percent)));
      safeURL(item.url);
    }
  }
  return view;
}
