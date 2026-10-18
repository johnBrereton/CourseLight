import { createRoot } from "react-dom/client";
import { GradeViewApp } from "../../shared/grades/GradeViewApp.jsx";
import { Gradebook } from "./Gradebook.jsx";
import { readGradebookResult } from "./tool-result.js";
import "./gradebook.css";

const root = createRoot(document.getElementById("gradebook-root"));
root.render(<GradeViewApp name="Gradebook" bridge={window.CourseLightBridge} onTeardown={() => root.unmount()}
  View={Gradebook} readResult={readGradebookResult} />);
