/* MCP Apps host transport. React owns the view; this bridge owns messaging. */
(() => {
  "use strict";
  let nextRequestId = 0;
  window.CourseLightBridge = {
    start({ onResult, onError, onContext, onTeardown, appName = "CourseLight" }) {
      if (window.parent === window) {
        onError("This component needs an MCP Apps host such as ChatGPT.");
        return () => {};
      }
      const requestId = `courselight-init-${++nextRequestId}`;
      let ready = false;
      let disposed = false;
      let parentOrigin = "*";
      let observer;
      let frame;
      let lastHeight = 0;
      const notify = (method, params) => window.parent.postMessage({ jsonrpc: "2.0", method, params }, parentOrigin);
      const timeout = window.setTimeout(() => {
        cleanup();
        onError("The host couldn’t connect to this view. Ask ChatGPT to show it again.");
      }, 15000);
      function resize() {
        cancelAnimationFrame(frame);
        frame = requestAnimationFrame(() => {
          const element = document.querySelector(".planner");
          if (disposed || !element) return;
          const height = Math.ceil(element.getBoundingClientRect().height);
          if (ready && height !== lastHeight) {
            lastHeight = height;
            notify("ui/notifications/size-changed", { height });
          }
        });
      }
      function cleanup() {
        if (disposed) return;
        disposed = true;
        clearTimeout(timeout);
        cancelAnimationFrame(frame);
        observer?.disconnect();
        window.removeEventListener("message", receive);
      }
      function receive(event) {
        if (disposed || event.source !== window.parent) return;
        if (parentOrigin !== "*" && event.origin !== parentOrigin) return;
        const message = event.data;
        if (!message || message.jsonrpc !== "2.0") return;
        if (message.id === requestId && !message.method && !ready) {
          clearTimeout(timeout);
          if (message.error || !message.result) {
            cleanup();
            onError("The host couldn’t connect to this view. Ask ChatGPT to show it again.");
            return;
          }
          parentOrigin = event.origin && event.origin !== "null" ? event.origin : "*";
          ready = true;
          onContext(message.result.hostContext || {});
          notify("ui/notifications/initialized", {});
          observer = new ResizeObserver(resize);
          const element = document.querySelector(".planner");
          if (element) observer.observe(element);
          resize();
          return;
        }
        if (!ready) return;
        if (message.method === "ui/notifications/tool-result") {
          if (message.params?.isError) onError("The requested data wasn’t returned. Ask ChatGPT to check the connection and try again.");
          else onResult(message.params?.structuredContent, message.params?._meta || {});
        } else if (message.method === "ui/notifications/host-context-changed") {
          onContext(message.params || {});
        } else if (message.method === "ui/notifications/tool-cancelled") {
          onError("Loading this view was cancelled. You can ask ChatGPT to try again.");
        } else if (message.method === "ui/resource-teardown" && message.id !== undefined) {
          cleanup();
          window.parent.postMessage({ jsonrpc: "2.0", id: message.id, result: {} }, parentOrigin);
          onTeardown?.();
        }
      }
      window.addEventListener("message", receive);
      window.parent.postMessage({ jsonrpc: "2.0", id: requestId, method: "ui/initialize", params: {
        appInfo: { name: appName, version: "1.0.0" },
        appCapabilities: {}, protocolVersion: "2026-01-26"
      } }, "*");
      return cleanup;
    }
  };
})();
