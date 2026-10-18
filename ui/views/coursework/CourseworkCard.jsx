import { CourseCard } from "../courses/CourseCard.jsx";
import { CourseworkRow } from "./CourseworkRow.jsx";

export function CourseworkCard(props) {
  const { course, timezone } = props;
  const countLabel = [course.assignments.length ? `${course.assignments.length} due` : "",
    course.other_work.length ? `${course.other_work.length} to check` : ""].filter(Boolean).join(" · ");
  return (
    <CourseCard {...props} countLabel={countLabel}
      emptyMessage="No weekly assignments or possible coursework returned."
      emptyHint="This search can miss work. Check CourseSite and your syllabus.">
      {course.other_work.length > 0 && <details className="coursework-group">
        <summary>Other coursework to check ({course.other_work.length})</summary>
        <p className="coursework-note">Possible matches. Undated items may belong to another week.</p>
        <ul className="assignment-list">
          {course.other_work.map((item) => <CourseworkRow key={item.id} item={item} timezone={timezone} />)}
        </ul>
      </details>}
    </CourseCard>
  );
}
