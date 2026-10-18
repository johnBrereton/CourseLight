import { createRoot } from "react-dom/client";
import { ReservationsApp } from "./ReservationsApp.jsx";
import "./reservations.css";

const root = createRoot(document.getElementById("reservations-root"));
root.render(<ReservationsApp bridge={window.CourseLightBridge} onTeardown={() => root.unmount()} />);
