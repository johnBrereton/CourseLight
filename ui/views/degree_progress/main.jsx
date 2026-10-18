import { createRoot } from "react-dom/client";
import { DegreeProgressApp } from "./DegreeProgressApp.jsx";
import "./degree-progress.css";

const root = createRoot(document.getElementById("degree-progress-root"));
root.render(<DegreeProgressApp bridge={window.CourseLightBridge} onTeardown={() => root.unmount()} />);
