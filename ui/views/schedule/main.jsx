import { createRoot } from "react-dom/client";
import { ScheduleApp } from "./ScheduleApp.jsx";
import "./schedule.css";

const root = createRoot(document.getElementById("schedule-root"));
root.render(<ScheduleApp bridge={window.CourseLightBridge} onTeardown={() => root.unmount()} />);
