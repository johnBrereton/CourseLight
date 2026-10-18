export function readMaterialsResult(result) {
  const fail = () => { throw new Error("Invalid materials result"); };
  const text = (value, max = 240) => typeof value === "string" && value.trim().length > 0 && value.length <= max;
  const id = (value) => Number.isSafeInteger(value) && value > 0;
  if (!result || result.schema_version !== "materials.v1" || !id(result.course_id) || !text(result.course_name) ||
      !text(result.site_url, 2048) || !Array.isArray(result.groups) || result.groups.length > 6) fail();
  const site = new URL(result.site_url);
  if (site.protocol !== "https:" || site.username || site.password || site.search || site.hash) fail();
  const groups = result.groups.map((group) => {
    if (!text(group.title) || !Array.isArray(group.items) || group.items.length > 60 ||
        (group.notice != null && !text(group.notice, 500))) fail();
    const items = group.items.map((item) => {
      if (!id(item.module_id) || !text(item.name) || !text(item.section) || !text(item.source_url, 2048) ||
          (item.filename != null && !text(item.filename)) ||
          (item.size != null && (!Number.isSafeInteger(item.size) || item.size < 0))) fail();
      const sourcePrefix = `${result.site_url}/mod/`;
      if (!item.source_url.startsWith(sourcePrefix) ||
          !new RegExp(`^(resource|folder|page|url|book)/view\\.php\\?id=${item.module_id}$`).test(item.source_url.slice(sourcePrefix.length))) fail();
      if (item.download_url != null) {
        const prefix = `${result.site_url}/pluginfile.php/`;
        if (!text(item.download_url, 2048) || !item.filename || !item.download_url.startsWith(prefix) ||
            !/^\d+\/mod_(resource|folder)\/content\/\d+\/[^?#]+\?forcedownload=1$/.test(item.download_url.slice(prefix.length))) fail();
        const url = new URL(item.download_url);
        if (url.origin !== site.origin || decodeURIComponent(url.pathname).split("/").some((part) => part === "." || part === "..")) fail();
      }
      return { module_id: item.module_id, name: item.name, section: item.section, source_url: item.source_url,
        filename: item.filename, size: item.size, download_url: item.download_url };
    });
    return { title: group.title, items, notice: group.notice };
  });
  return { course_id: result.course_id, groups };
}
