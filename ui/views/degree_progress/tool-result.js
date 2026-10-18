const source = "https://dw-prod.ec.lehigh.edu/responsiveDashboard/worksheets/WEB31";
const number = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0;
const progress = (value) => value === null || (number(value) && value <= 100);
const label = (value) => typeof value === "string" && value.length > 0 && value.length <= 240;

export function readDegreeProgressResult(view) {
  if (!view || view.schema_version !== "degree_progress.v1" || view.source_url !== source ||
      !Array.isArray(view.degrees) || view.degrees.length > 12 ||
      !view.degrees.every(label) || !progress(view.completion_percent) ||
      !Array.isArray(view.majors) || view.majors.length > 12 ||
      !view.majors.every((major) => major && label(major.name) && progress(major.completion_percent)) ||
      !(view.cumulative_gpa === null || number(view.cumulative_gpa)) ||
      !(view.audit_date === null || (typeof view.audit_date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(view.audit_date) &&
        Number.isFinite(Date.parse(`${view.audit_date}T00:00:00Z`))))) {
    throw new Error("Invalid degree progress result");
  }
  return view;
}
