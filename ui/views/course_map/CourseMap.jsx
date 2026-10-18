import { useMemo, useState } from "react";
import { MapCanvas } from "../../shared/maps/MapCanvas.jsx";

export function CourseMap({ view, token, theme }) {
  const [hiddenCourses, setHiddenCourses] = useState(() => new Set());
  const courses = useMemo(() => [...new Map(view.days.flatMap(day => day.stops)
    .map(stop => [stop.course, { name: stop.course, title: stop.title }])).values()], [view.days]);
  const places = useMemo(() => {
    const visible = new Set(view.days.flatMap(day => day.stops)
      .filter(stop => !hiddenCourses.has(stop.course)).map(stop => stop.place_id));
    return view.places.filter(place => visible.has(place.id));
  }, [view, hiddenCourses]);
  const allHidden = courses.length > 0 && courses.every(course => hiddenCourses.has(course.name));
  const unlocated = [...new Set(view.days.flatMap(day => day.stops)
    .filter(stop => !hiddenCourses.has(stop.course) && !stop.place_id).map(stop => stop.course))];

  function toggleCourse(name) {
    setHiddenCourses(previous => {
      const next = new Set(previous);
      if (next.has(name)) next.delete(name); else next.add(name);
      return next;
    });
  }

  return <section className="course-map" aria-label="Course locations">
    <div className="map-course-toggles" role="group" aria-label="Courses shown on the map">
      {courses.map(course => <button key={course.name} aria-pressed={!hiddenCourses.has(course.name)}
        title={course.title} onClick={() => toggleCourse(course.name)}>
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
          <path d="m3 8 3.2 3.2L13 4.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>{course.name}
      </button>)}
    </div>
    <MapCanvas places={places} token={token} theme={theme}
      emptyMessage={allHidden ? "Choose a course to show its location" : "No class locations available for this week"} />
    {unlocated.length > 0 && <p className="map-location-note" role="status">Location unavailable: {unlocated.join(" · ")}</p>}
  </section>;
}
