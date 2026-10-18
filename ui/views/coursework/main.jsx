import { createRoot } from "react-dom/client";
import { CourseworkApp } from "./CourseworkApp.jsx";
import "./coursework.css";

const root = createRoot(document.getElementById("coursework-root"));
root.render(<CourseworkApp bridge={window.CourseLightBridge} onTeardown={() => root.unmount()} />);
