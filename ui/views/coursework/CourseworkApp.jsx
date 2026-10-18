import { CoursesApp } from "../courses/CoursesApp.jsx";
import { CourseworkCard } from "./CourseworkCard.jsx";
import { readCourseworkResult } from "./tool-result.js";

const notice = (
  <aside className="coursework-risk" role="note" aria-label="Broader search limitations">
    <strong>Coursework · broader search</strong>
    <p>This keyword-based approach is riskier: matches may be unrelated or from another week,
      and real work can be missed. Verify them in CourseSite.</p>
  </aside>
);

export function CourseworkApp(props) {
  return <CoursesApp {...props} appName="CourseLight Coursework" readResult={readCourseworkResult}
    Card={CourseworkCard} notice={notice} />;
}
