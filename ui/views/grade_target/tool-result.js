import { check, text, percent, readCourse } from "../../shared/grades/result.js";

export function readGradeTargetResult(view) {
  const safeURL = readCourse(view, "grade_target.v1");
  check(Array.isArray(view.syllabi) && view.syllabi.length <= 6);
  for (const syllabus of view.syllabi) { check(text(syllabus.title)); safeURL(syllabus.url); }
  if (view.projection) {
    const projection = view.projection;
    safeURL(projection.source_url);
    check(percent(projection.target) && text(projection.explanation) && Array.isArray(projection.assumptions) &&
      projection.assumptions.length <= 4 && projection.assumptions.every(text) && Array.isArray(projection.work) &&
      projection.work.length > 0 && projection.work.length <= 80);
    for (const item of projection.work) check(text(item.name) && percent(item.weight) && item.weight > 0 && (item.percent == null || percent(item.percent)));
    check(Math.abs(projection.work.reduce((sum, item) => sum + item.weight, 0) - 100) <= 0.001 &&
      new Set(projection.work.map((item) => item.name)).size === projection.work.length);
  }
  return view;
}
