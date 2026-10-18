import { createRoot } from "react-dom/client";
import { MapViewApp } from "../../shared/maps/MapViewApp.jsx";
import { StudyRoom } from "./StudyRoom.jsx";
import { readStudyRoom } from "./tool-result.js";
import "../../shared/maps/maps.css";

const root = createRoot(document.getElementById("study-room-root"));
root.render(<MapViewApp bridge={window.CourseLightBridge} readResult={readStudyRoom} View={StudyRoom}
  name="CourseLight Study Room" onTeardown={() => root.unmount()} />);
