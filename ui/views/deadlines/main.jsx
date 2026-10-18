import { createRoot } from "react-dom/client";
import { DeadlinesApp } from "./DeadlinesApp.jsx";
import "./deadlines.css";

const root = createRoot(document.getElementById("deadlines-root"));
root.render(<DeadlinesApp bridge={window.CourseLightBridge} onTeardown={() => root.unmount()} />);
