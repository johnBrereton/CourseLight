import { useLayoutEffect, useRef } from "react";
import { CourseCard } from "./CourseCard.jsx";
import { CourseLightHeader } from "../../shared/components/CourseLightHeader.jsx";

export function Courses({ status, view, Card = CourseCard, notice }) {
  const stackRef = useRef(null);
  useLayoutEffect(() => {
    const stack = stackRef.current;
    if (!stack) return;
    // Measure natural content, not the matched button height, so rows can also
    // shrink after a resize. Long names stay readable without fixed-height clips.
    const summaries = [...stack.querySelectorAll(".course-summary")];
    const matchHeights = () => {
      const height = Math.ceil(Math.max(0, ...summaries.map((row) => row.getBoundingClientRect().height)));
      stack.style.setProperty("--course-row-height", `${height}px`);
    };
    const observer = new ResizeObserver(matchHeights);
    summaries.forEach((row) => observer.observe(row));
    matchHeights();
    return () => observer.disconnect();
  }, [status, view]);

  const firstDue = view?.courses.findIndex((course) => course.assignments.length > 0) ?? -1;
  return (
    <main className="planner courses-panel" aria-label="Courses">
      <CourseLightHeader />
      {status === "ready" && notice}
      {status === "loading" && <p className="view-status" role="status">Reading your courses…</p>}
      {status === "error" && (
        <div className="view-status" role="alert">
          <p className="state-title">Courses couldn’t load.</p>
          <p>Ask ChatGPT to check the CourseSite connection and try again.</p>
        </div>
      )}
      {status === "ready" && view && (view.courses.length ? (
        <div className="course-stack" ref={stackRef}>
          {view.courses.map((course, index) => (
            <Card key={`${view.week_start}:${course.id}`} course={course}
              timezone={view.timezone} initiallyOpen={index === (firstDue < 0 ? 0 : firstDue)} />
          ))}
        </div>
      ) : <p className="view-status">No courses selected. Ask ChatGPT to show your current semester.</p>)}
    </main>
  );
}
