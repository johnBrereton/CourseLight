import { createRoot } from "react-dom/client";
import { GradeViewApp } from "../../shared/grades/GradeViewApp.jsx";
import { GradeTarget } from "./GradeTarget.jsx";
import { readGradeTargetResult } from "./tool-result.js";
import "./target.css";

const root = createRoot(document.getElementById("grade-target-root"));
root.render(<GradeViewApp name="Grade target" bridge={window.CourseLightBridge} onTeardown={() => root.unmount()}
  View={GradeTarget} readResult={readGradeTargetResult} />);
