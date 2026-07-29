 console.log("SafeGate AI frontend loaded successfully.");

const startButton = document.getElementById("start-camera-button");
const stopButton = document.getElementById("stop-camera-button");
const cameraFeed = document.getElementById("live-camera-feed");
const cameraStatusBadge = document.getElementById("camera-status-badge");
const cameraSystemText = document.getElementById("camera-system-text");
const workerForm = document.getElementById("worker-session-form");
const workerInput = document.getElementById("worker-id-input");
const sessionMessage = document.getElementById("session-message");
const emptyWorkerState = document.getElementById("worker-empty-state");
const liveWorkerState = document.getElementById("worker-live-state");
const clearSessionButton = document.getElementById("clear-session-button");


function setCameraStatus(isRunning) {
    if (cameraStatusBadge) {
        cameraStatusBadge.innerHTML = isRunning
            ? '<span class="status-dot online"></span>Live'
            : '<span class="status-dot warning"></span>Stopped';
    }

    if (cameraSystemText) {
        cameraSystemText.textContent = isRunning ? "Connected" : "Stopped";
    }

    if (startButton) {
        startButton.disabled = isRunning;
    }

    if (stopButton) {
        stopButton.disabled = !isRunning;
    }
}


function setSessionMessage(message, isError = false) {
    if (!sessionMessage) {
        return;
    }

    sessionMessage.textContent = message;
    sessionMessage.classList.toggle("error", isError);
}


function setGateState(gateState) {
    const gate = document.getElementById("gate-status");
    const text = document.getElementById("gate-status-text");
    const icon = document.getElementById("gate-icon");

    if (!gate || !text || !icon) {
        return;
    }

    const status = gateState?.state || "LOCKED";
    const reason = document.getElementById("gate-status-reason");
    const timestamp = document.getElementById("gate-status-timestamp");

    gate.classList.remove("locked", "open", "review");

    if (status === "OPEN") {
        gate.classList.add("open");
        text.textContent = "OPEN — SIMULATION";
        icon.textContent = "🔓";
    } else if (status === "REVIEW") {
        gate.classList.add("review");
        text.textContent = "REVIEW REQUIRED";
        icon.textContent = "⚠️";
    } else {
        gate.classList.add("locked");
        text.textContent = "LOCKED";
        icon.textContent = "🔒";
    }

    if (reason) {
        reason.textContent = gateState?.reason || "Fail-safe locked state.";
    }

    if (timestamp) {
        timestamp.textContent = gateState?.timestamp
            ? `Updated ${new Date(gateState.timestamp).toLocaleTimeString()}`
            : "";
    }
}


function setGateMonitorValue(elementId, value) {
    const element = document.getElementById(elementId);

    if (element) {
        element.textContent = value;
    }
}


function renderGateMonitor(state) {
    const gate = state.gate || {};
    const timestamp = gate.timestamp
        ? new Date(gate.timestamp).toLocaleString()
        : "Not available";
    const worker = state.worker
        ? `${state.worker.name} (${state.worker.worker_id})`
        : "No worker selected";
    const decision = state.decision
        ? state.decision.status
        : "No access decision";

    setGateMonitorValue("gate-monitor-state", gate.state || "LOCKED");
    setGateMonitorValue("gate-monitor-mode", gate.mode || "SIMULATOR");
    setGateMonitorValue("gate-monitor-command", gate.last_command || "LOCK");
    setGateMonitorValue("gate-monitor-reason", gate.reason || "Fail-safe locked state.");
    setGateMonitorValue("gate-monitor-timestamp", timestamp);
    setGateMonitorValue(
        "gate-monitor-camera",
        state.camera_running ? "Running" : "Stopped"
    );
    setGateMonitorValue("gate-monitor-worker", worker);
    setGateMonitorValue("gate-monitor-decision", decision);
}


function renderSettingsStatus(state) {
    const gate = state.gate || {};

    setGateMonitorValue(
        "settings-camera-status",
        state.camera_running ? "Running" : "Stopped"
    );
    setGateMonitorValue(
        "settings-camera-detail",
        state.error || "No camera error reported."
    );
    setGateMonitorValue("settings-gate-state", gate.state || "LOCKED");
    setGateMonitorValue("settings-gate-mode", gate.mode || "SIMULATOR");
    setGateMonitorValue(
        "settings-gate-command",
        gate.last_command || "LOCK"
    );
    setGateMonitorValue(
        "settings-gate-reason",
        gate.reason || "Fail-safe locked state."
    );
}


function renderLiveState(state) {
    setCameraStatus(state.camera_running);
    renderGateMonitor(state);
    renderSettingsStatus(state);

    if (!state.worker) {
        if (emptyWorkerState) {
            emptyWorkerState.hidden = false;
        }

        if (liveWorkerState) {
            liveWorkerState.hidden = true;
        }

        setGateState(state.gate);
        return;
    }

    emptyWorkerState.hidden = true;
    liveWorkerState.hidden = false;

    const decision = state.decision;
    const frames = decision ? decision.frames_checked : 0;

    document.getElementById("worker-avatar").textContent =
        state.worker.name.charAt(0).toUpperCase();
    document.getElementById("worker-name").textContent = state.worker.name;
    document.getElementById("worker-role").textContent = state.worker.role;
    document.getElementById("worker-id").textContent = state.worker.worker_id;
    document.getElementById("worker-policy").textContent =
        state.worker.helmet_exempt
            ? "Approved helmet exemption"
            : "Helmet required";
    document.getElementById("helmet-evidence").textContent = decision
        ? `${decision.helmet_frames}/${frames} frames`
        : "Collecting frames";
    document.getElementById("vest-evidence").textContent = decision
        ? `${decision.vest_frames}/${frames} frames`
        : "Collecting frames";
    document.getElementById("decision-reason").textContent = decision
        ? `${decision.status}: ${decision.reason}`
        : "Initialising verification session.";

    setGateState(state.gate);
}


async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok || data.success === false) {
        throw new Error(data.message || "Request failed.");
    }

    return data;
}


async function refreshLiveState() {
    try {
        const state = await requestJson("/api/live-state");
        renderLiveState(state);
    } catch (error) {
        console.error("Could not load live state:", error);
    }
}


async function startCamera() {
    try {
        const state = await requestJson("/camera/start", {method: "POST"});

        if (cameraFeed) {
            cameraFeed.src = `/video-feed?timestamp=${Date.now()}`;
        }

        renderLiveState(state);
    } catch (error) {
        setSessionMessage(error.message, true);
    }
}


async function stopCamera() {
    try {
        const state = await requestJson("/camera/stop", {method: "POST"});

        if (cameraFeed) {
            cameraFeed.removeAttribute("src");
        }

        renderLiveState(state);
    } catch (error) {
        setSessionMessage(error.message, true);
    }
}


async function startWorkerSession(event) {
    event.preventDefault();

    if (!workerInput || !workerInput.value) {
        setSessionMessage("Select an active worker first.", true);
        return;
    }

    try {
        const result = await requestJson("/api/session", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({worker_id: workerInput.value}),
        });

        setSessionMessage(result.message);
        renderLiveState(result.state);
    } catch (error) {
        setSessionMessage(error.message, true);
    }
}


async function clearWorkerSession() {
    try {
        await requestJson("/api/session/clear", {method: "POST"});
        setSessionMessage("Verification session cleared.");
        await refreshLiveState();
    } catch (error) {
        setSessionMessage(error.message, true);
    }
}


startButton?.addEventListener("click", startCamera);
stopButton?.addEventListener("click", stopCamera);
workerForm?.addEventListener("submit", startWorkerSession);
clearSessionButton?.addEventListener("click", clearWorkerSession);

refreshLiveState();
window.setInterval(refreshLiveState, 1000);
