"use strict";

(() => {
  let csrf = "";
  let busy = false;
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
    if (busy) return;
    busy = true;
    try {
      await api(path, { ...payload, operation_id: operationId(operationPrefix) });
      message(label);
      await refresh();
    } catch (error) {
      message(`Operation rejected (${error.message}).`, true);
    } finally {
      busy = false;
    }
  }

  function actionButton(label, action, container) {
    const button = document.createElement("button");
    button.textContent = label;
    button.addEventListener("click", () => {
      if (container.role === "client" && action !== "start" && !window.confirm(`${label} this transient client? Its in-memory key, package, and proof identity will be erased. The container can restart only as a fresh empty session.`)) return;
      mutate("/api/manager/v1/container-action", { action, container_id: container.id }, `${label} requested for ${container.name}.`, action);
    });
    return button;
  }

  function render(containers) {
    const target = byId("containers");
    target.replaceChildren();
    const hasClient = containers.some((container) => container.role === "client");
    byId("create-client").disabled = hasClient;
    byId("create-client").title = hasClient ? "Destroy the current client before creating another." : "";
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
        destroy.addEventListener("click", () => {
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
    byId("system-state").textContent = labels[shutdownStatus] || "Unavailable";
    byId("stop-system").disabled = shutdownStatus === "stopping";
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
      byId("create-client").addEventListener("click", () => mutate("/api/manager/v1/clients", {}, "New transient client created.", "create-client"));
      byId("stop-system").addEventListener("click", async () => {
        if (!window.confirm("Stop the complete integrated system?")) return;
        try {
          const result = await api("/api/manager/v1/system-stop", { operation_id: operationId("system-stop") });
          if (result.shutdown_status !== "stopping") throw new Error("shutdown_not_started");
          byId("system-state").textContent = "Stopping";
          message("System shutdown is in progress. This page becomes unavailable only after every required stop succeeds.");
        } catch (error) { message(error.message, true); }
      });
      window.setInterval(() => { if (!busy) refresh().catch(() => { byId("system-state").textContent = "Unavailable"; }); }, 3000);
    } catch (_error) {
      byId("system-state").textContent = "Unavailable";
      message("Manager controller is unavailable.", true);
    }
  }

  initialize();
})();
