"use strict";

(() => {
  const API_VERSION = "LOCUS-client-api-v1";
  const state = {
    catalog: null,
    enrollmentReceipt: "",
    successorReceipt: "",
    bootstrap: null,
    recoveryInput: null,
  };

  const byId = (id) => document.getElementById(id);
  const all = (selector) => Array.from(document.querySelectorAll(selector));

  function operationId(prefix) {
    const bytes = new Uint8Array(12);
    crypto.getRandomValues(bytes);
    return `${prefix}-${Array.from(bytes, (item) => item.toString(16).padStart(2, "0")).join("")}`;
  }

  function announce(message, error = false) {
    const banner = byId("global-status");
    banner.textContent = message;
    banner.classList.toggle("error", error);
    banner.hidden = false;
    banner.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function clearAnnouncement() {
    const banner = byId("global-status");
    banner.hidden = true;
    banner.textContent = "";
    banner.classList.remove("error");
  }

  async function api(path, payload = null) {
    const options = {
      method: payload === null ? "GET" : "POST",
      cache: "no-store",
      credentials: "omit",
      redirect: "error",
      referrerPolicy: "no-referrer",
      headers: payload === null ? {} : { "Content-Type": "application/json" },
    };
    if (payload !== null) options.body = JSON.stringify(payload);
    const response = await fetch(path, options);
    const value = await response.json();
    if (!response.ok) {
      const category = typeof value.category === "string" ? value.category : "operation_rejected";
      throw new Error(category);
    }
    return value;
  }

  function setBusy(form, busy) {
    all("button, input, select, textarea").forEach((control) => {
      if (form.contains(control)) control.disabled = busy;
    });
  }

  function selectOptions(select, items, valueField, labelField, placeholder = "") {
    select.replaceChildren();
    if (placeholder) {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = placeholder;
      option.disabled = true;
      option.selected = true;
      select.append(option);
    }
    items.forEach((item) => {
      const option = document.createElement("option");
      option.value = item[valueField];
      option.textContent = item[labelField];
      select.append(option);
    });
  }

  function createField(label, type, className) {
    const wrap = document.createElement("div");
    wrap.className = "field-wrap";
    const labelElement = document.createElement("label");
    const input = document.createElement(type === "select" ? "select" : "input");
    const id = `${className}-${crypto.getRandomValues(new Uint32Array(1))[0]}`;
    input.id = id;
    input.className = className;
    input.required = true;
    input.autocomplete = "off";
    input.spellcheck = false;
    if (type !== "select") input.type = type;
    labelElement.htmlFor = id;
    labelElement.textContent = label;
    wrap.append(labelElement, input);
    return { wrap, input };
  }

  function cueMember(index) {
    const member = document.createElement("div");
    member.className = "cue-member";
    const marker = document.createElement("span");
    marker.className = "cue-index";
    marker.textContent = String(index + 1).padStart(2, "0");
    const fields = document.createElement("div");
    fields.className = "cue-fields";
    member.append(marker, fields);
    return { member, fields };
  }

  function renderCueFields(container, policyId) {
    container.replaceChildren();
    for (let index = 0; index < 3; index += 1) {
      const { member, fields } = cueMember(index);
      if (policyId === "LOCUS-canonical-email-set-v1") {
        fields.classList.add("single");
        const email = createField("Canonical email address", "email", "cue-email");
        email.input.maxLength = 254;
        fields.append(email.wrap);
      } else if (policyId === "LOCUS-canonical-phone-set-v1") {
        fields.classList.add("single");
        const phone = createField("E.164 phone number", "tel", "cue-phone");
        phone.input.placeholder = "+352621000001";
        phone.input.maxLength = 16;
        fields.append(phone.wrap);
      } else if (policyId === "LOCUS-quantized-coordinate-set-v1") {
        const latitude = createField("Latitude", "text", "cue-latitude");
        const longitude = createField("Longitude", "text", "cue-longitude");
        latitude.input.inputMode = "decimal";
        longitude.input.inputMode = "decimal";
        fields.append(latitude.wrap, longitude.wrap);
      } else {
        const latitude = createField("Latitude", "text", "cue-latitude");
        const longitude = createField("Longitude", "text", "cue-longitude");
        const contactType = createField("Contact type", "select", "cue-contact-type");
        ["email", "phone"].forEach((value) => {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = value === "email" ? "Email" : "Phone";
          contactType.input.append(option);
        });
        const contact = createField("Contact value", "text", "cue-contact");
        fields.append(latitude.wrap, longitude.wrap, contactType.wrap, contact.wrap);
      }
      container.append(member);
    }
  }

  function cueInput(container, policyId) {
    const members = Array.from(container.querySelectorAll(".cue-member"));
    if (members.length !== 3) throw new Error("input_rejected");
    if (policyId === "LOCUS-canonical-email-set-v1") {
      return members.map((item) => item.querySelector(".cue-email").value);
    }
    if (policyId === "LOCUS-canonical-phone-set-v1") {
      return members.map((item) => item.querySelector(".cue-phone").value);
    }
    if (policyId === "LOCUS-quantized-coordinate-set-v1") {
      return members.map((item) => ({
        latitude: item.querySelector(".cue-latitude").value,
        longitude: item.querySelector(".cue-longitude").value,
      }));
    }
    return members.map((item) => ({
      location: {
        latitude: item.querySelector(".cue-latitude").value,
        longitude: item.querySelector(".cue-longitude").value,
      },
      person: {
        type: item.querySelector(".cue-contact-type").value,
        value: item.querySelector(".cue-contact").value,
      },
    }));
  }

  function clearCueFields(container) {
    container.querySelectorAll("input").forEach((input) => { input.value = ""; });
  }

  function previewLines(normalized) {
    if (Array.isArray(normalized.emails)) return normalized.emails;
    if (Array.isArray(normalized.phones)) return normalized.phones;
    if (Array.isArray(normalized.coordinates)) {
      return normalized.coordinates.map((item) => `${(item.latitude_e4 / 10000).toFixed(4)}, ${(item.longitude_e4 / 10000).toFixed(4)}`);
    }
    if (Array.isArray(normalized.pairs)) {
      return normalized.pairs.map((item) => `${(item.location.latitude_e4 / 10000).toFixed(4)}, ${(item.location.longitude_e4 / 10000).toFixed(4)} · ${item.person.value}`);
    }
    return ["Validated by the enrolled policy"];
  }

  function renderPreview(target, normalized) {
    target.replaceChildren();
    const heading = document.createElement("h3");
    heading.textContent = "Normalized selection preview";
    const list = document.createElement("ol");
    previewLines(normalized).forEach((line) => {
      const item = document.createElement("li");
      item.textContent = line;
      list.append(item);
    });
    target.append(heading, list);
    target.hidden = false;
  }

  function renderDefinition(target, entries) {
    target.replaceChildren();
    entries.forEach(([label, value]) => {
      const wrap = document.createElement("div");
      const term = document.createElement("dt");
      const description = document.createElement("dd");
      term.textContent = label;
      description.textContent = String(value);
      wrap.append(term, description);
      target.append(wrap);
    });
  }

  function renderRolePlacement(target, roles) {
    target.replaceChildren();
    roles.forEach((role) => {
      const row = document.createElement("div");
      row.className = "role-row";
      const name = document.createElement("strong");
      const count = document.createElement("span");
      name.textContent = role.role;
      count.textContent = `${role.bytes.toLocaleString()} bytes · ${role.items} item${role.items === 1 ? "" : "s"}`;
      row.append(name, count);
      target.append(row);
    });
  }

  function downloadReceipt(receipt, filename) {
    if (!receipt) return;
    const value = JSON.stringify({ receipt }, null, 2);
    const url = URL.createObjectURL(new Blob([value], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.rel = "noopener noreferrer";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  async function receiptFromFile(file) {
    if (!file || file.size < 1 || file.size > 32768) throw new Error("input_rejected");
    const text = await file.text();
    try {
      const value = JSON.parse(text);
      if (typeof value.receipt !== "string") throw new Error("input_rejected");
      return value.receipt;
    } catch (_error) {
      const trimmed = text.trim();
      if (!trimmed) throw new Error("input_rejected");
      return trimmed;
    }
  }

  function switchPanel(panelId) {
    all(".workflow-panel").forEach((panel) => {
      const selected = panel.id === panelId;
      panel.hidden = !selected;
      panel.classList.toggle("active", selected);
    });
    all(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.panel === panelId));
    if (panelId !== "recovery-panel") {
      state.recoveryInput = null;
      clearCueFields(byId("recovery-cues"));
    }
    if (panelId === "inspector-panel" && !byId("inspector-receipt").value) {
      byId("inspector-receipt").value = state.successorReceipt || state.enrollmentReceipt;
    }
    clearAnnouncement();
    byId("workspace").focus();
  }

  function bindNavigation() {
    all(".nav-item").forEach((button) => button.addEventListener("click", () => switchPanel(button.dataset.panel)));
    all(".go-recovery").forEach((button) => button.addEventListener("click", () => {
      byId("recovery-receipt").value = state.enrollmentReceipt;
      switchPanel("recovery-panel");
    }));
  }

  function bindKeyMode() {
    all('input[name="key-mode"]').forEach((input) => input.addEventListener("change", () => {
      const imported = document.querySelector('input[name="key-mode"]:checked').value === "import-synthetic";
      byId("key-import-wrap").hidden = !imported;
      if (!imported) byId("key-import").value = "";
      all(".choice-card").forEach((card) => card.classList.toggle("selected", card.querySelector("input").checked));
    }));
  }

  async function previewEnrollment() {
    const policyId = byId("policy-select").value;
    const value = await api("/api/v1/preview-policy", {
      api_version: API_VERSION,
      policy_id: policyId,
      recovery_input: cueInput(byId("enrollment-cues"), policyId),
    });
    renderPreview(byId("enrollment-preview"), value.normalized_preview);
    announce("Structured input is valid. Review the normalized selection before enrollment.");
  }

  function enrollmentProtectedKey() {
    const mode = document.querySelector('input[name="key-mode"]:checked').value;
    return { mode, hex: mode === "import-synthetic" ? byId("key-import").value : null };
  }

  async function enroll(event) {
    event.preventDefault();
    const form = event.currentTarget;
    setBusy(form, true);
    clearAnnouncement();
    try {
      const policyId = byId("policy-select").value;
      const result = await api("/api/v1/enroll", {
        api_version: API_VERSION,
        deployment_profile_id: byId("profile-select").value,
        operation_id: operationId("ui-enroll"),
        policy_id: policyId,
        protected_key: enrollmentProtectedKey(),
        recovery_input: cueInput(byId("enrollment-cues"), policyId),
        suite_id: byId("suite-select").value,
      });
      state.enrollmentReceipt = result.receipt;
      renderDefinition(byId("enrollment-summary"), [
        ["Public fingerprint", result.public_fingerprint],
        ["Suite", result.suite_id],
        ["Threshold", `${result.threshold.k}-of-${result.threshold.n}`],
        ["Policy", result.policy_id],
        ["Epoch", result.epoch],
        ["Disposal", result.disposal_status],
      ]);
      try {
        const inspection = await api("/api/v1/inspect", { receipt: result.receipt });
        renderRolePlacement(byId("enrollment-placement"), inspection.role_placement);
      } catch (_error) {
        const unavailable = document.createElement("p");
        unavailable.className = "field-help";
        unavailable.textContent = "Redacted placement is unavailable for this session.";
        byId("enrollment-placement").replaceChildren(unavailable);
      }
      byId("enrollment-result").hidden = false;
      byId("key-import").value = "";
      clearCueFields(byId("enrollment-cues"));
      byId("enrollment-preview").replaceChildren();
      byId("enrollment-preview").hidden = true;
      announce("Enrollment completed. Export the public receipt before closing this session.");
      byId("enrollment-result").scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (error) {
      announce(`Enrollment was rejected (${error.message}).`, true);
    } finally {
      setBusy(form, false);
    }
  }

  async function bootstrap(event) {
    event.preventDefault();
    const form = event.currentTarget;
    setBusy(form, true);
    clearAnnouncement();
    try {
      const receipt = byId("recovery-receipt").value.trim();
      const result = await api("/api/v1/bootstrap", { receipt });
      state.bootstrap = result;
      byId("bootstrap-suite").textContent = result.suite_id;
      renderDefinition(byId("bootstrap-summary"), [
        ["Policy", result.policy_id],
        ["Threshold", `${result.threshold.k}-of-${result.threshold.n}`],
        ["Authorization", `${result.authorization_quorum}-of-5`],
        ["Epoch", result.epoch],
      ]);
      renderCueFields(byId("recovery-cues"), result.policy_id);
      byId("bootstrap-result").hidden = false;
      byId("recovery-form").hidden = false;
      byId("recovery-result").hidden = true;
      byId("successor-form").hidden = true;
      byId("successor-result").hidden = true;
      announce("Bootstrap authenticated. The enrolled suite and policy are fixed.");
    } catch (error) {
      state.bootstrap = null;
      announce(`Bootstrap was rejected (${error.message}).`, true);
    } finally {
      setBusy(form, false);
    }
  }

  async function recover(event) {
    event.preventDefault();
    if (!state.bootstrap) return;
    const form = event.currentTarget;
    setBusy(form, true);
    clearAnnouncement();
    try {
      const recoveryInput = cueInput(byId("recovery-cues"), state.bootstrap.policy_id);
      const result = await api("/api/v1/recover", {
        api_version: API_VERSION,
        operation_id: operationId("ui-recover"),
        receipt: byId("recovery-receipt").value.trim(),
        recovery_input: recoveryInput,
      });
      state.recoveryInput = recoveryInput;
      renderDefinition(byId("recovery-summary"), [
        ["Public fingerprint", result.public_fingerprint],
        ["Suite", result.suite_id],
        ["Epoch", result.epoch],
        ["Identity check", result.key_identity_verified ? "Verified" : "Rejected"],
      ]);
      byId("recovery-result").hidden = false;
      announce("Recovery completed and the protected-key public identity matched.");
      byId("recovery-result").scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (error) {
      state.recoveryInput = null;
      announce(`Recovery was rejected (${error.message}).`, true);
    } finally {
      clearCueFields(byId("recovery-cues"));
      setBusy(form, false);
    }
  }

  async function successor(event) {
    event.preventDefault();
    if (!state.bootstrap || state.recoveryInput === null) {
      announce("Recover successfully before preparing a successor.", true);
      return;
    }
    const form = event.currentTarget;
    setBusy(form, true);
    try {
      const result = await api("/api/v1/successor", {
        api_version: API_VERSION,
        operation_id: operationId("ui-successor"),
        receipt: byId("recovery-receipt").value.trim(),
        recovery_input: state.recoveryInput,
        rotate_protected_key: byId("rotate-key").checked,
        successor_deployment_profile_id: byId("successor-profile").value,
        successor_suite_id: byId("successor-suite").value,
      });
      state.successorReceipt = result.receipt;
      state.recoveryInput = null;
      renderDefinition(byId("successor-summary"), [
        ["Suite", result.suite_id],
        ["Epoch", result.epoch],
        ["Threshold", `${result.threshold.k}-of-${result.threshold.n}`],
        ["Key rotated", result.protected_key_rotated ? "Yes" : "No"],
      ]);
      byId("successor-result").hidden = false;
      announce("Successor enrollment completed. Export its new public receipt.");
    } catch (error) {
      announce(`Successor enrollment was rejected (${error.message}).`, true);
    } finally {
      setBusy(form, false);
    }
  }

  async function inspect(event) {
    event.preventDefault();
    const form = event.currentTarget;
    setBusy(form, true);
    clearAnnouncement();
    try {
      const result = await api("/api/v1/inspect", { receipt: byId("inspector-receipt").value.trim() });
      byId("metric-backup").textContent = result.byte_counts.cloud_backup.toLocaleString();
      byId("metric-parties").textContent = result.byte_counts.party_records_total.toLocaleString();
      byId("metric-bundle").textContent = result.byte_counts.recovery_bundle.toLocaleString();
      renderRolePlacement(byId("role-placement"), result.role_placement);
      renderDefinition(byId("public-identifiers"), Object.entries(result.public_identifiers));
      renderDefinition(byId("safe-digests"), Object.entries(result.safe_digests));
      const categories = byId("message-categories");
      categories.replaceChildren();
      result.message_categories.forEach((category) => {
        const tag = document.createElement("span");
        tag.className = "tag";
        tag.textContent = category;
        categories.append(tag);
      });
      byId("inspector-result").hidden = false;
      announce("Safe metadata inspection completed.");
    } catch (error) {
      announce(`Inspection was rejected (${error.message}).`, true);
    } finally {
      setBusy(form, false);
    }
  }

  function clearTransientDocumentState() {
    state.recoveryInput = null;
    byId("key-import").value = "";
    clearCueFields(byId("enrollment-cues"));
    clearCueFields(byId("recovery-cues"));
    byId("enrollment-preview").replaceChildren();
    byId("enrollment-preview").hidden = true;
  }

  async function initialize() {
    try {
      state.catalog = await api("/api/v1/catalog");
      selectOptions(byId("suite-select"), state.catalog.suites, "suite_id", "label", "Choose a suite");
      selectOptions(byId("successor-suite"), state.catalog.suites, "suite_id", "label", "Choose a suite");
      selectOptions(byId("profile-select"), state.catalog.profiles, "profile_id", "label");
      selectOptions(byId("successor-profile"), state.catalog.profiles, "profile_id", "label");
      selectOptions(byId("policy-select"), state.catalog.policies, "policy_id", "label");
      renderCueFields(byId("enrollment-cues"), byId("policy-select").value);
      bindNavigation();
      bindKeyMode();
      byId("policy-select").addEventListener("change", () => {
        renderCueFields(byId("enrollment-cues"), byId("policy-select").value);
        byId("enrollment-preview").hidden = true;
      });
      byId("preview-enrollment").addEventListener("click", () => previewEnrollment().catch((error) => announce(`Input was rejected (${error.message}).`, true)));
      byId("enrollment-form").addEventListener("submit", enroll);
      byId("bootstrap-form").addEventListener("submit", bootstrap);
      byId("recovery-form").addEventListener("submit", recover);
      byId("successor-form").addEventListener("submit", successor);
      byId("inspector-form").addEventListener("submit", inspect);
      byId("show-successor").addEventListener("click", () => { byId("successor-form").hidden = false; byId("successor-form").scrollIntoView({ behavior: "smooth" }); });
      byId("download-receipt").addEventListener("click", () => downloadReceipt(state.enrollmentReceipt, "locus-recovery-receipt.json"));
      byId("download-successor-receipt").addEventListener("click", () => downloadReceipt(state.successorReceipt, "locus-successor-receipt.json"));
      byId("receipt-file").addEventListener("change", async (event) => {
        try { byId("recovery-receipt").value = await receiptFromFile(event.target.files[0]); }
        catch (error) { announce(`Receipt file was rejected (${error.message}).`, true); }
        event.target.value = "";
      });
      document.addEventListener("copy", (event) => event.preventDefault());
      document.addEventListener("cut", (event) => event.preventDefault());
      window.addEventListener("pagehide", clearTransientDocumentState);
    } catch (_error) {
      announce("The local research client API is unavailable.", true);
    }
  }

  initialize();
})();
