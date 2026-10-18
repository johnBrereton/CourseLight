import { createRoot } from "react-dom/client";
import { CoursesApp } from "./CoursesApp.jsx";
import "./courses.css";

const root = createRoot(document.getElementById("courses-root"));
root.render(<CoursesApp bridge={window.CourseLightBridge} onTeardown={() => root.unmount()} />);
