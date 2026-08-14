"use strict";

(() => {
  let csrf = "";
  let busy = false;
  let systemStopping = false;
  const byId = (id) => document.getElementById(id);

  function operationId(prefix) {
    const bytes = new Uint8Array(12);
    crypto.getRandomValues(bytes);
    return `${prefix}-${Array.from(bytes, (item) => item.toString(16).padStart(2, "0")).join("")}`;
  }

  function message(text, error = false) {
    const node = byId("message");
    node.textContent = text;
    node.classList.toggle("error", error);
    node.hidden = false;
  }

  async function api(path, payload = null) {
    const options = { method: payload === null ? "GET" : "POST", cache: "no-store", credentials: "omit", redirect: "error", referrerPolicy: "no-referrer", headers: {} };
    if (payload !== null) {
      options.headers = { "Content-Type": "application/json", "X-LOCUS-CSRF": csrf };
      options.body = JSON.stringify(payload);
    }
    const response = await fetch(path, options);
    const value = await response.json();
    if (!response.ok) throw new Error(value.category || "operation_rejected");
    return value;
  }

  async function mutate(path, payload, label, operationPrefix) {
    // Block at the logic level, independent of whichever control's
    // disabled state a caller may or may not have already checked: once
    // the system is stopping, no further Manager mutation may be sent.
    if (busy || systemStopping) return false;
    busy = true;
    let succeeded = false;
    try {
      await api(path, { ...payload, operation_id: operationId(operationPrefix) });
      message(label);
      await refresh();
      succeeded = true;
    } catch (error) {
      message(`Operation rejected (${error.message}).`, true);
    } finally {
      busy = false;
    }
    return succeeded;
  }

  function actionButton(label, action, container) {
    const button = document.createElement("button");
    button.textContent = label;
    button.disabled = systemStopping;
    button.title = systemStopping ? "System shutdown is in progress." : "";
    button.addEventListener("click", () => {
      if (systemStopping) return;
      if (container.role === "client" && action !== "start" && !window.confirm(`${label} this transient client? Its in-memory key, package, and proof identity will be erased. The container can restart only as a fresh empty session.`)) return;
      mutate("/api/manager/v1/container-action", { action, container_id: container.id }, `${label} requested for ${container.name}.`, action);
    });
    return button;
  }

  function render(containers) {
    const target = byId("containers");
    target.replaceChildren();
    const hasClient = containers.some((container) => container.role === "client");
    byId("create-client").disabled = hasClient || systemStopping;
    byId("create-client").title = systemStopping ? "System shutdown is in progress." : hasClient ? "Destroy the current client before creating another." : "";
    containers.forEach((container) => {
      const fragment = byId("container-card").content.cloneNode(true);
      fragment.querySelector(".role").textContent = container.role === "client" ? "Transient client" : "Infrastructure";
      fragment.querySelector(".name").textContent = container.name;
      fragment.querySelector(".state").textContent = container.state;
      const lifecycle = container.self_destroy_status;
      fragment.querySelector(".health").textContent = container.role === "client" && lifecycle !== "ready" ? `${container.health} · self-destroy ${lifecycle}` : container.health;
      fragment.querySelector(".client-id").textContent = container.client_id || "—";
      const actions = fragment.querySelector(".actions");
      if (!["bootstrap", "manager-controller", "manager-ui"].includes(container.role)) {
        if (container.state === "running") {
          actions.append(actionButton("Stop", "stop", container), actionButton("Restart", "restart", container), actionButton("Kill", "kill", container));
        } else {
          actions.append(actionButton("Start", "start", container));
        }
      }
      if (container.role === "client") {
        // Navigation only (no Manager mutation) -- left reachable even while
        // stopping so the operator can see what a client last showed; it
        // cannot itself cause the failures this lock is meant to prevent.
        if (container.url && container.state === "running") {
          const link = document.createElement("a");
          link.href = container.url;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          link.textContent = "Open Client UI";
          link.className = "button-link primary";
          actions.prepend(link);
        }
        const destroy = document.createElement("button");
        destroy.className = "danger";
        destroy.textContent = "Destroy client";
        destroy.disabled = systemStopping;
        destroy.title = systemStopping ? "System shutdown is in progress." : "";
        destroy.addEventListener("click", () => {
          if (systemStopping) return;
          if (window.confirm(`Destroy ${container.client_id}? Its in-memory key will be lost.`)) {
            mutate("/api/manager/v1/client-destroy", { container_id: container.id }, "Client destroyed.", "destroy-client");
          }
        });
        actions.append(destroy);
      }
      target.append(fragment);
    });
  }

  async function refresh() {
    const value = await api("/api/manager/v1/status");
    const labels = { ready: "Ready", stopping: "Stopping", failed: "Shutdown failed" };
    const shutdownStatus = value.shutdown_status;
    // Every mutating control in the Manager UI (create, per-container
    // actions, destroy) is gated on this flag once the system reports
    // "stopping", so the operator cannot race further mutations against
    // the shutdown sequence. "Stop system" itself and "Refresh" (a
    // read-only GET) remain available so the operator can still see
    // progress and, if shutdown fails, retry.
    systemStopping = shutdownStatus === "stopping";
    byId("system-state").textContent = labels[shutdownStatus] || "Unavailable";
    byId("stop-system").disabled = systemStopping;
    if (shutdownStatus === "failed") message("System shutdown did not complete. Review the remaining containers and retry Stop system.", true);
    const failedClient = value.containers.some((container) => container.role === "client" && container.self_destroy_status === "failed");
    if (failedClient) message("Client self-destruction did not complete. Use Destroy client to retry removal.", true);
    render(value.containers);
  }

  async function initialize() {
    try {
      const session = await api("/api/manager/v1/session");
      csrf = session.csrf_token;
      await refresh();
      byId("refresh").addEventListener("click", () => refresh().catch((error) => message(error.message, true)));
      byId("create-client").addEventListener("click", async () => {
        const button = byId("create-client");
        const idleLabel = button.textContent;
        button.disabled = true;
        button.textContent = "Creating…";
        const created = await mutate("/api/manager/v1/clients", {}, "New transient client created.", "create-client");
        button.textContent = idleLabel;
        // On success, refresh()/render() already set the correct disabled
        // state (only one transient client is allowed at a time, and
        // systemStopping if a stop began meanwhile). Otherwise -- failure,
        // another operation already in flight, or the system started
        // stopping just as this was clicked -- no client was created, so
        // restore the button to whatever the current systemStopping state
        // actually allows rather than unconditionally re-enabling it.
        if (!created) button.disabled = systemStopping;
      });
      byId("stop-system").addEventListener("click", async () => {
        const button = byId("stop-system");
        if (!window.confirm("Stop the complete integrated system?")) return;
        // Disable synchronously so a rapid double-click cannot send a
        // second system-stop request while the first is still in flight.
        button.disabled = true;
        try {
          const result = await api("/api/manager/v1/system-stop", { operation_id: operationId("system-stop") });
          if (result.shutdown_status !== "stopping") throw new Error("shutdown_not_started");
        } catch (error) {
          message(error.message, true);
          button.disabled = systemStopping;
          return;
        }
        message("System shutdown is in progress. This page becomes unavailable only after every required stop succeeds.");
        try {
          // Refresh immediately rather than waiting for the next 3-second
          // poll, so every create/action/destroy control locks right away
          // instead of staying clickable for up to 3 more seconds.
          await refresh();
        } catch (_error) {
          // The stop request itself already succeeded; a refresh hiccup
          // here does not mean shutdown failed -- the next poll recovers.
        }
      });
      window.setInterval(() => { if (!busy) refresh().catch(() => { byId("system-state").textContent = "Unavailable"; }); }, 3000);
    } catch (_error) {
      byId("system-state").textContent = "Unavailable";
      message("Manager controller is unavailable.", true);
    }
  }

  initialize();
})();
