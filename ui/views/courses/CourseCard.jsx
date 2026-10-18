import { useId, useLayoutEffect, useRef, useState } from "react";
import chevron from "../../shared/assets/icons/chevron-down.svg";
import arrow from "../../shared/assets/icons/arrow-up-right.svg";
import { GlassSurface } from "../../shared/components/GlassSurface.jsx";
import { AssignmentRow } from "./AssignmentRow.jsx";

export function CourseCard({ course, timezone, initiallyOpen = false, children, countLabel,
  emptyMessage = "No assignments returned for this week.",
  emptyHint = "Check CourseSite for other activities and syllabus deadlines." }) {
  const [open, setOpen] = useState(initiallyOpen);
  const headingRef = useRef(null);
  const contentRef = useRef(null);
  const [materialHeight, setMaterialHeight] = useState(0);
  useLayoutEffect(() => {
    // Keep the optical surface at its full natural size. Only the disclosure
    // clips/reveals it, so opening a card never stretches its refraction map.
    const measure = () => setMaterialHeight(
      headingRef.current.offsetHeight + contentRef.current.offsetHeight,
    );
    const observer = new ResizeObserver(measure);
    observer.observe(headingRef.current);
    observer.observe(contentRef.current);
    measure();
    return () => observer.disconnect();
  }, []);

  const panelId = useId();
  const buttonId = useId();
  const count = course.assignments.length;
  const totals = countLabel ?? (count ? `${count} due` : "");
  const badge = course.status === "unavailable" ? "Unavailable" : totals || "0 due";
  const warnings = course.warnings.filter((warning) =>
    warning !== "Some personal deadline extensions could not be checked. Verify dates in CourseSite.");
  return (
    <article className={`course-glass${open ? " is-open" : ""}`}
      style={{ "--course-material-height": `${materialHeight}px` }}>
      <GlassSurface className="course-material" aria-hidden="true" />
      <h2 className="course-heading" ref={headingRef}>
        <button id={buttonId} className="course-toggle" type="button"
          aria-expanded={open} aria-controls={panelId} onClick={() => setOpen((value) => !value)}>
          <span className="course-summary">
            <span className="course-labels">
              <span className="course-title">{course.name}</span>
              {course.code !== course.name && <span className="course-code">{course.code}</span>}
            </span>
            <span className={`due-count${course.status === "unavailable" ? " is-unavailable" : ""}`}>{badge}</span>
            <img className="course-chevron" src={chevron} alt="" aria-hidden="true" />
          </span>
        </button>
      </h2>
      <div id={panelId} className="course-disclosure" role="region" aria-labelledby={buttonId}
        aria-hidden={!open} inert={!open}>
        <div className="course-content">
          <div className="course-content-inner" ref={contentRef}>
            {count > 0 && <ul className="assignment-list">
              {course.assignments.map((assignment) => <AssignmentRow key={assignment.id}
                assignment={assignment} timezone={timezone} />)}
            </ul>}
            {children}
            {course.status !== "unavailable" && count === 0 && !children && (
              <div className="course-empty">
                <p>{emptyMessage}</p>
                <span>{emptyHint}</span>
              </div>
            )}
            {warnings.length > 0 && <div className="course-notices" role="note">
              {warnings.map((warning) => <p key={warning}>{warning}</p>)}
            </div>}
            {course.undated_count > 0 && <p className="undated-note">
              {course.undated_count} {course.undated_count === 1 ? "assignment has" : "assignments have"} no posted due date.
            </p>}
            <a className="course-link" href={course.url} target="_blank" rel="noopener noreferrer">
              Open CourseSite <img className="external-icon" src={arrow} alt="" aria-hidden="true" />
            </a>
          </div>
        </div>
      </div>
    </article>
  );
}
