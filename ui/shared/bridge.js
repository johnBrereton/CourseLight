/* MCP Apps host transport. React owns the view; this bridge owns messaging. */
(() => {
  "use strict";
  let nextRequestId = 0;
  let connection;
  window.CourseLightBridge = {
    updateModelContext(data) {
      return connection ? connection("ui/update-model-context", { content: [{ type: "text", text: `CourseLight room request data: ${JSON.stringify(data)}` }] })
        : Promise.reject(new Error("The host is not connected."));
    },
    callTool(name, args) {
      return connection ? connection("tools/call", { name, arguments: args }) : Promise.reject(new Error("The host is not connected."));
    },
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
      const pending = new Map();
      const request = (method, params) => new Promise((resolve, reject) => {
        if (!ready || disposed) { reject(new Error("The host is not connected.")); return; }
        const id = `courselight-${++nextRequestId}`;
        const timer = setTimeout(() => {
          pending.delete(id);
          reject(new Error("The response timed out. Check request status before making another booking."));
        }, 90000);
        pending.set(id, { resolve, reject, timer });
        window.parent.postMessage({ jsonrpc: "2.0", id, method, params }, parentOrigin);
      });
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
        if (connection === request) connection = undefined;
        for (const call of pending.values()) {
          clearTimeout(call.timer);
          call.reject(new Error("The host disconnected. Check 25Live before making another booking."));
        }
        pending.clear();
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
          connection = request;
          onContext(message.result.hostContext || {});
          notify("ui/notifications/initialized", {});
          observer = new ResizeObserver(resize);
          const element = document.querySelector(".planner");
          if (element) observer.observe(element);
          resize();
          return;
        }
        if (!ready) return;
        if (message.id !== undefined && !message.method && pending.has(message.id)) {
          const call = pending.get(message.id);
          pending.delete(message.id);
          clearTimeout(call.timer);
          if (message.error) call.reject(new Error(message.error.message || "The tool call failed."));
          else call.resolve(message.result);
          return;
        }
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
