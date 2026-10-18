import { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { GlassProvider } from "../../shared/components/GlassSurface.jsx";
import { CourseLightHeader } from "../../shared/components/CourseLightHeader.jsx";
import { StudyRoom } from "./StudyRoom.jsx";
import { readStudyRoom } from "./tool-result.js";
import "../../shared/maps/maps.css";
import "./study-rooms.css";

const bridge = window.CourseLightBridge;
const root = createRoot(document.getElementById("study-room-root"));

function App() {
  const [state, setState] = useState({ status: "loading" });
  const [theme, setTheme] = useState();
  const receive = useCallback((result, metadata = {}) => {
    const view = readStudyRoom(result);
    const token = metadata["courselight/mapkit"]?.token;
    setState(previous => ({ status: "ready", view,
      token: typeof token === "string" && token.length <= 8192 ? token : previous.token || "" }));
  }, []);
  useEffect(() => bridge.start({
    appName: "CourseLight Study Rooms",
    onResult(result, metadata) {
      try { receive(result, metadata); } catch { setState({ status: "error" }); }
    },
    onError() { setState({ status: "error" }); },
    onContext(context) {
      if (["light", "dark"].includes(context.theme)) {
        document.documentElement.dataset.theme = context.theme;
        setTheme(context.theme);
      }
    },
    onTeardown() { root.unmount(); },
  }), [receive]);
  return <GlassProvider><main className="planner map-panel" aria-label="Study rooms">
    <CourseLightHeader />
    {state.status === "loading" && <p className="map-message" role="status">Finding study rooms…</p>}
    {state.status === "error" && <p className="map-message" role="alert">Room data couldn’t load. Ask ChatGPT to check your Lehigh connection.</p>}
    {state.status === "ready" && <StudyRoom view={state.view} token={state.token} theme={theme} bridge={bridge} onView={receive} />}
  </main></GlassProvider>;
}

root.render(<App />);
