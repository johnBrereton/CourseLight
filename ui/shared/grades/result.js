export const text = (value) => typeof value === "string" && value.length > 0 && value.length <= 2048;
export const percent = (value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 100;
export const check = (condition) => { if (!condition) throw new Error("Invalid grade result"); };

export function readCourse(view, schema) {
  check(view && view.schema_version === schema && text(view.course_name) &&
    Number.isSafeInteger(view.course_id) && view.course_id > 0 && text(view.site_url));
  const site = new URL(view.site_url);
  check(site.protocol === "https:" && !site.username && !site.password && !site.search && !site.hash);
  return (value) => {
    check(text(value));
    const url = new URL(value);
    check(url.protocol === "https:" && !url.username && !url.password && !url.hash);
    const prefix = view.site_url + "/";
    check((value.startsWith(prefix) && /^(course\/view|grade\/report\/user\/index|mod\/(resource|url|page)\/view)\.php\?id=\d+$/.test(value.slice(prefix.length))) ||
      /^https:\/\/www\.gradescope\.com\/courses\/\d+(\/assignments\/\d+)?$/.test(value));
  };
}
