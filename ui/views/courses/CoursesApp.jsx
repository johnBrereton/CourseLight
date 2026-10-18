import { useEffect, useState } from "react";
import { Courses } from "./Courses.jsx";
import { readCoursesResult } from "./tool-result.js";
import { GlassProvider } from "../../shared/components/GlassSurface.jsx";

export function CoursesApp({ bridge, onTeardown, readResult = readCoursesResult,
  Card, notice, appName = "CourseLight Courses" }) {
  const [state, setState] = useState({ status: "loading", view: null });
  useEffect(() => bridge.start({
    appName,
    onResult(result) {
      try {
        setState({ status: "ready", view: readResult(result) });
      } catch {
        setState({ status: "error", view: null });
      }
    },
    onError() { setState({ status: "error", view: null }); },
    onContext(context) {
      if (["light", "dark"].includes(context.theme)) document.documentElement.dataset.theme = context.theme;
    },
    onTeardown,
  }), [bridge, onTeardown, readResult, appName]);
  return <GlassProvider><Courses status={state.status} view={state.view} Card={Card} notice={notice} /></GlassProvider>;
}
