import lehighBrown from "../assets/branding/lehigh-university-brown.png";
import lehighWhite from "../assets/branding/lehigh-university-white.png";
import { CourseLightMark } from "./CourseLightMark.jsx";

export function CourseLightHeader() {
  return (
    <header className="courselight-header">
      <div className="courselight-brand">
        <CourseLightMark className="courselight-mark" />
        <h1>CourseLight</h1>
      </div>
      <div className="courselight-campus">
        <img className="lehigh-logo lehigh-logo-light" src={lehighBrown} alt="Lehigh University" width="800" height="173" />
        <img className="lehigh-logo lehigh-logo-dark" src={lehighWhite} alt="Lehigh University" width="800" height="167" />
      </div>
    </header>
  );
}
