import { createRoot } from "react-dom/client";
import { MaterialsApp } from "./MaterialsApp.jsx";
import "./materials.css";

const root = createRoot(document.getElementById("materials-root"));
root.render(<MaterialsApp bridge={window.CourseLightBridge} onTeardown={() => root.unmount()} />);
