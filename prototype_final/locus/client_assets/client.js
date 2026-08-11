"use strict";

(() => {
  const API_VERSION = "LOCUS-client-api-v2";
  const PACKAGE_TYPE = "application/vnd.locus.recovery-package+json";
  const state = { csrf: "", catalog: null, downloadId: "", packageDownloaded: false, imported: null, keyLoaded: false, revealTimer: null };
  const byId = (id) => document.getElementById(id);
  const all = (selector) => Array.from(document.querySelectorAll(selector));

  function operationId(prefix) {
    const bytes = new Uint8Array(12);
    crypto.getRandomValues(bytes);
    return `${prefix}-${Array.from(bytes, (item) => item.toString(16).padStart(2, "0")).join("")}`;
  }

  function announce(message, error = false) {
    const target = byId("status");
    target.textContent = message;
    target.classList.toggle("error", error);
    target.hidden = false;
  }

  async function jsonApi(path, payload = null) {
    const options = {
      method: payload === null ? "GET" : "POST",
      cache: "no-store",
      credentials: "omit",
      redirect: "error",
      referrerPolicy: "no-referrer",
      headers: payload === null ? {} : { "Content-Type": "application/json", "X-LOCUS-CSRF": state.csrf },
    };
    if (payload !== null) options.body = JSON.stringify(payload);
    const response = await fetch(path, options);
    const value = await response.json();
    if (!response.ok) throw new Error(typeof value.category === "string" ? value.category : "operation_rejected");
    return value;
  }

  function setBusy(container, busy) {
    container.querySelectorAll("button, input, select").forEach((control) => {
      if (busy) {
        control.dataset.locusPriorDisabled = control.disabled ? "yes" : "no";
        control.disabled = true;
      } else if (control.dataset.locusPriorDisabled) {
        control.disabled = control.dataset.locusPriorDisabled === "yes";
        delete control.dataset.locusPriorDisabled;
      }
    });
  }

  function selectOptions(select, values, valueField, labelField) {
    select.replaceChildren();
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value[valueField];
      option.textContent = value[labelField];
      select.append(option);
    });
  }

  function renderDefinition(target, entries) {
    target.replaceChildren();
    entries.forEach(([label, value]) => {
      const row = document.createElement("div");
      const term = document.createElement("dt");
      const description = document.createElement("dd");
      term.textContent = label;
      description.textContent = String(value);
      row.append(term, description);
      target.append(row);
    });
  }

  function renderPhases(target, phases) {
    target.replaceChildren();
    phases.forEach((phase) => {
      const item = document.createElement("li");
      item.textContent = phase.replaceAll("_", " ");
      target.append(item);
    });
  }

  function createInput(label, className, type = "text") {
    const wrap = document.createElement("label");
    wrap.textContent = label;
    const input = document.createElement("input");
    input.className = className;
    input.type = type;
    input.required = true;
    input.autocomplete = "off";
    input.spellcheck = false;
    wrap.append(input);
    return wrap;
  }

  function renderCues(target, policyId) {
    target.replaceChildren();
    for (let index = 0; index < 3; index += 1) {
      const row = document.createElement("div");
      row.className = "cue-row";
      const number = document.createElement("span");
      number.className = "cue-number";
      number.textContent = String(index + 1).padStart(2, "0");
      const fields = document.createElement("div");
      fields.className = "cue-fields";
      if (policyId === "LOCUS-canonical-email-set-v1") {
        fields.classList.add("single"); fields.append(createInput("Canonical email address", "cue-email", "email"));
      } else if (policyId === "LOCUS-canonical-phone-set-v1") {
        fields.classList.add("single"); fields.append(createInput("E.164 phone number", "cue-phone", "tel"));
      } else if (policyId === "LOCUS-quantized-coordinate-set-v1") {
        fields.append(createInput("Latitude", "cue-latitude"), createInput("Longitude", "cue-longitude"));
      } else {
        fields.append(createInput("Latitude", "cue-latitude"), createInput("Longitude", "cue-longitude"));
        const type = document.createElement("label");
        type.textContent = "Contact type";
        const select = document.createElement("select");
        select.className = "cue-contact-type";
        ["email", "phone"].forEach((kind) => { const option = document.createElement("option"); option.value = kind; option.textContent = kind; select.append(option); });
        type.append(select);
        fields.append(type, createInput("Contact value", "cue-contact"));
      }
      row.append(number, fields);
      target.append(row);
    }
  }

  function cueInput(target, policyId) {
    const rows = Array.from(target.querySelectorAll(".cue-row"));
    if (policyId === "LOCUS-canonical-email-set-v1") return rows.map((row) => row.querySelector(".cue-email").value);
    if (policyId === "LOCUS-canonical-phone-set-v1") return rows.map((row) => row.querySelector(".cue-phone").value);
    if (policyId === "LOCUS-quantized-coordinate-set-v1") return rows.map((row) => ({ latitude: row.querySelector(".cue-latitude").value, longitude: row.querySelector(".cue-longitude").value }));
    return rows.map((row) => ({
      location: { latitude: row.querySelector(".cue-latitude").value, longitude: row.querySelector(".cue-longitude").value },
      person: { type: row.querySelector(".cue-contact-type").value, value: row.querySelector(".cue-contact").value },
    }));
  }

  function clearCues(target) { target.querySelectorAll("input").forEach((input) => { input.value = ""; }); }

  function hideKey() {
    if (state.revealTimer !== null) window.clearTimeout(state.revealTimer);
    state.revealTimer = null;
    byId("private-key-value").textContent = "";
    byId("private-key-panel").hidden = true;
    byId("hide-key").disabled = true;
  }

  function showKey(result) {
    hideKey();
    byId("private-key-value").textContent = result.private_key;
    byId("private-key-panel").hidden = false;
    byId("hide-key").disabled = false;
    byId("key-fingerprint").textContent = result.public_fingerprint;
    byId("key-state").textContent = "Key loaded";
    byId("reveal-key").disabled = false;
    state.keyLoaded = true;
    state.revealTimer = window.setTimeout(hideKey, 30000);
  }

  function selectedProfile() {
    return state.catalog.profiles.find((profile) => profile.profile_id === byId("profile").value);
  }

  function renderEnrollmentParties() {
    const profile = selectedProfile();
    if (!profile) return;
    const holders = Array.from({ length: profile.threshold.n }, (_item, index) => index + 1).join(", ");
    byId("enrollment-parties").textContent = `${profile.threshold.k}-of-${profile.threshold.n} recovery holders: ${holders}. Authorization remains a separate 4-of-5 quorum.`;
  }

  async function generateKey() {
    if (state.keyLoaded && !window.confirm("Replace the current volatile private key with a newly generated key?")) return;
    const result = await jsonApi("/api/v2/key/generate", { api_version: API_VERSION, operation_id: operationId("generate") });
    showKey(result);
    announce("A fresh synthetic private key is loaded in this client.");
  }

  async function revealKey() {
    const result = await jsonApi("/api/v2/key/reveal", { api_version: API_VERSION });
    showKey(result);
  }

  async function preview() {
    const policyId = byId("policy").value;
    const result = await jsonApi("/api/v2/preview-policy", { api_version: API_VERSION, policy_id: policyId, recovery_input: cueInput(byId("enrollment-cues"), policyId) });
    byId("preview-result").textContent = `Validated ${Array.isArray(result.normalized_preview) ? result.normalized_preview.length : 3} structured members through ${result.policy_id}.`;
    byId("preview-result").hidden = false;
  }

  async function enroll(event) {
    event.preventDefault();
    setBusy(document.body, true);
    hideKey();
    announce("Enrollment is running through CuePolicy, threshold setup, encryption, and authenticated publication.");
    try {
      const policyId = byId("policy").value;
      const result = await jsonApi("/api/v2/enroll", {
        api_version: API_VERSION,
        deployment_profile_id: byId("profile").value,
        operation_id: operationId("enroll"),
        policy_id: policyId,
        recovery_input: cueInput(byId("enrollment-cues"), policyId),
        suite_id: byId("suite").value,
      });
      state.downloadId = result.download_id;
      state.packageDownloaded = false;
      renderDefinition(byId("enrollment-summary"), [["Fingerprint", result.public_fingerprint], ["Suite", result.suite_id], ["Suite profile", result.suite_profile_id], ["Deployment profile", result.deployment_profile_id], ["Policy", result.policy_id], ["Threshold", `${result.threshold.k}-of-${result.threshold.n}`], ["Epoch", result.epoch]]);
      renderPhases(byId("enrollment-phases"), result.completed_phases);
      byId("enrollment-result").hidden = false;
      clearCues(byId("enrollment-cues"));
      announce("Enrollment completed. Download the encrypted package before destroying this client.");
    } catch (error) { announce(`Enrollment rejected (${error.message}).`, true); }
    finally { setBusy(document.body, false); }
  }

  async function downloadPackage() {
    if (!state.downloadId) return;
    const response = await fetch("/api/v2/package/export", {
      method: "POST", cache: "no-store", credentials: "omit", redirect: "error", referrerPolicy: "no-referrer",
      headers: { "Content-Type": "application/json", "X-LOCUS-CSRF": state.csrf },
      body: JSON.stringify({ api_version: API_VERSION, download_id: state.downloadId }),
    });
    if (!response.ok) { const value = await response.json(); throw new Error(value.category || "package_export_rejected"); }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "locus-encrypted-recovery-package.locus";
    anchor.rel = "noopener noreferrer";
    document.body.append(anchor); anchor.click(); anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    state.packageDownloaded = true;
    announce("Encrypted recovery package downloaded. It contains no private key or recovery input.");
  }

  function renderRecoveryParties(result) {
    const target = byId("recovery-parties");
    target.replaceChildren();
    result.holder_ids.forEach((holderId, index) => {
      const label = document.createElement("label");
      label.className = "party-option";
      const input = document.createElement("input");
      input.type = "checkbox"; input.value = String(holderId); input.checked = index < result.threshold.k;
      const name = document.createElement("span"); name.textContent = `Party ${holderId}`;
      label.append(input, name); target.append(label);
    });
    byId("party-guidance").textContent = `Choose exactly ${result.threshold.k} of the ${result.threshold.n} authenticated recovery holders. This does not change the separate 4-of-5 authorization quorum.`;
  }

  async function importPackage(file) {
    state.imported = null;
    byId("package-result").hidden = true;
    byId("recovery-form").hidden = true;
    byId("recovery-result").hidden = true;
    byId("package-summary").replaceChildren();
    byId("recovery-parties").replaceChildren();
    clearCues(byId("recovery-cues"));
    if (!file || file.size < 1 || file.size > 3 * 1024 * 1024) throw new Error("package_import_rejected");
    announce("Authenticating the package against discovery, current state, storage, and party summaries.");
    const response = await fetch("/api/v2/package/import", {
      method: "POST", cache: "no-store", credentials: "omit", redirect: "error", referrerPolicy: "no-referrer",
      headers: { "Content-Type": PACKAGE_TYPE, "X-LOCUS-CSRF": state.csrf }, body: await file.arrayBuffer(),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.category || "package_import_rejected");
    state.imported = result;
    renderDefinition(byId("package-summary"), [["Suite", result.suite_id], ["Suite profile", result.suite_profile_id], ["Deployment profile", result.deployment_profile_id], ["Policy", result.policy_id], ["Threshold", `${result.threshold.k}-of-${result.threshold.n}`], ["Authorization", `${result.authorization_quorum}-of-5`], ["Epoch", result.epoch], ["Expected fingerprint", result.public_fingerprint]]);
    renderRecoveryParties(result);
    renderCues(byId("recovery-cues"), result.policy_id);
    byId("package-result").hidden = false;
    byId("recovery-form").hidden = false;
    byId("recovery-result").hidden = true;
    announce("The package, current pointer, descriptor, and party summaries are authenticated.");
  }

  async function recover(event) {
    event.preventDefault();
    if (!state.imported) return;
    setBusy(document.body, true); hideKey();
    announce("Recovery is requesting authorization and the selected threshold parties.");
    try {
      const selected = Array.from(byId("recovery-parties").querySelectorAll("input:checked"), (input) => Number(input.value)).sort((left, right) => left - right);
      const result = await jsonApi("/api/v2/recover", {
        api_version: API_VERSION, operation_id: operationId("recover"), recovery_input: cueInput(byId("recovery-cues"), state.imported.policy_id), selected_holder_ids: selected,
      });
      renderDefinition(byId("recovery-summary"), [["Previous fingerprint", result.previous_public_fingerprint || "No previous key"], ["Restored fingerprint", result.public_fingerprint], ["Identity check", result.key_identity_verified ? "Verified" : "Rejected"], ["Key slot", result.key_replaced ? "Replaced" : "Unchanged"]]);
      renderPhases(byId("recovery-phases"), result.completed_phases);
      byId("key-fingerprint").textContent = result.public_fingerprint;
      byId("key-state").textContent = "Recovered key loaded";
      byId("reveal-key").disabled = false;
      state.keyLoaded = true;
      byId("recovery-result").hidden = false;
      clearCues(byId("recovery-cues"));
      announce("Recovery succeeded and the client key slot was atomically replaced.");
    } catch (error) { announce(`Recovery rejected (${error.message}). The current key was not replaced.`, true); }
    finally { setBusy(document.body, false); }
  }

  async function destroyClient() {
    const warning = state.downloadId && !state.packageDownloaded
      ? "The encrypted recovery package has not been downloaded. Destroying this client now will permanently lose its volatile private key. Continue?"
      : "Destroy this client and permanently lose its volatile private key state?";
    if (!window.confirm(warning)) return;
    hideKey(); clearCues(byId("enrollment-cues")); clearCues(byId("recovery-cues"));
    try {
      await jsonApi("/api/v2/self-destroy", { api_version: API_VERSION, operation_id: operationId("destroy") });
      document.body.replaceChildren();
      const message = document.createElement("main");
      message.className = "workspace card";
      const heading = document.createElement("h1"); heading.textContent = "Client destruction requested";
      const copy = document.createElement("p"); copy.textContent = "This client container and its volatile key state are being removed. Return to the Manager UI to create a fresh client.";
      message.append(heading, copy); document.body.append(message);
    } catch (error) { announce(`Client destruction rejected (${error.message}).`, true); }
  }

  function clearDocumentSecrets() { hideKey(); clearCues(byId("enrollment-cues")); clearCues(byId("recovery-cues")); }

  async function initialize() {
    try {
      const session = await jsonApi("/api/v2/session");
      state.csrf = session.csrf_token;
      byId("client-id").textContent = session.client_id;
      byId("client-identity").textContent = `${session.client_identity_profile}: ${session.client_identity}`;
      byId("proof-thumbprint").textContent = `Proof key ${session.proof_key_thumbprint}`;
      state.keyLoaded = session.key_loaded;
      if (session.key_loaded) { byId("key-state").textContent = "Key loaded"; byId("reveal-key").disabled = false; byId("key-fingerprint").textContent = session.public_fingerprint; }
      state.catalog = await jsonApi("/api/v2/catalog");
      selectOptions(byId("suite"), state.catalog.suites, "suite_id", "label");
      selectOptions(byId("profile"), state.catalog.profiles, "profile_id", "label");
      selectOptions(byId("policy"), state.catalog.policies, "policy_id", "label");
      renderCues(byId("enrollment-cues"), byId("policy").value); renderEnrollmentParties();
      byId("generate-key").addEventListener("click", () => generateKey().catch((error) => announce(`Key generation rejected (${error.message}).`, true)));
      byId("reveal-key").addEventListener("click", () => revealKey().catch((error) => announce(`Key reveal rejected (${error.message}).`, true)));
      byId("reveal-recovered").addEventListener("click", () => revealKey().catch((error) => announce(`Key reveal rejected (${error.message}).`, true)));
      byId("hide-key").addEventListener("click", hideKey);
      byId("profile").addEventListener("change", renderEnrollmentParties);
      byId("policy").addEventListener("change", () => renderCues(byId("enrollment-cues"), byId("policy").value));
      byId("preview").addEventListener("click", () => preview().catch((error) => announce(`Input rejected (${error.message}).`, true)));
      byId("enrollment-form").addEventListener("submit", enroll);
      byId("download-package").addEventListener("click", () => downloadPackage().catch((error) => announce(`Package export rejected (${error.message}).`, true)));
      byId("package-file").addEventListener("change", async (event) => { setBusy(document.body, true); try { await importPackage(event.target.files[0]); } catch (error) { announce(`Package import rejected (${error.message}).`, true); } finally { event.target.value = ""; setBusy(document.body, false); } });
      byId("recovery-form").addEventListener("submit", recover);
      byId("destroy-client").addEventListener("click", destroyClient);
      document.addEventListener("copy", (event) => event.preventDefault());
      document.addEventListener("cut", (event) => event.preventDefault());
      window.addEventListener("pagehide", clearDocumentSecrets);
    } catch (_error) { announce("The managed Client API is unavailable.", true); }
  }

  initialize();
})();
