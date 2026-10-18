import { array, integer, isoDate, mapConfig, place, text } from "../../shared/maps/validate.js";

export function readCourseMap(view) {
  const fail = () => { throw new Error("Invalid course map"); };
  if (!view || view.schema_version !== "course_map.v1" || !/^\d{6}$/.test(view.term) || !text(view.term_label) ||
      view.timezone !== "America/New_York" || !mapConfig(view.map) || !isoDate(view.selected_date) ||
      !array(view.places, 100) || !view.places.every(place) ||
      !array(view.days, 7) || view.days.length !== 7 || !array(view.notices, 20) || !view.notices.every(note => text(note, 500))) fail();
  const places = new Set(view.places.map(item => item.id));
  if (places.size !== view.places.length || new Set(view.days.map(day => day.date)).size !== 7) fail();
  for (const day of view.days) {
    if (!isoDate(day.date) || !array(day.stops, 200)) fail();
    const stops = new Set();
    for (const stop of day.stops) {
      if (!text(stop.id, 60) || stops.has(stop.id) || !text(stop.course) || !text(stop.title) || !text(stop.location) ||
          !array(stop.instructors, 20) || !stop.instructors.every(name => text(name)) ||
          !integer(stop.start_minute, 0, 1439) || !integer(stop.end_minute, stop.start_minute + 1, 1440) ||
          !(stop.place_id === null || places.has(stop.place_id))) fail();
      stops.add(stop.id);
    }
  }
  if (!view.days.some(day => day.date === view.selected_date)) fail();
  return view;
}
