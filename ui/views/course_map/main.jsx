import { createRoot } from "react-dom/client";
import { MapViewApp } from "../../shared/maps/MapViewApp.jsx";
import { CourseMap } from "./CourseMap.jsx";
import { readCourseMap } from "./tool-result.js";
import "../../shared/maps/maps.css";

const root = createRoot(document.getElementById("course-map-root"));
root.render(<MapViewApp bridge={window.CourseLightBridge} readResult={readCourseMap} View={CourseMap}
  name="CourseLight Course Map" onTeardown={() => root.unmount()} />);
