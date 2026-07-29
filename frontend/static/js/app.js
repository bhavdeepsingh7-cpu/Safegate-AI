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


function setGateState(status) {
    const gate = document.getElementById("gate-status");
    const text = document.getElementById("gate-status-text");
    const icon = document.getElementById("gate-icon");

    if (!gate || !text || !icon) {
        return;
    }

    gate.classList.remove("locked", "open", "review");

    if (status === "ACCESS GRANTED") {
        gate.classList.add("open");
        text.textContent = "OPEN — SIMULATION";
        icon.textContent = "🔓";
    } else if (status === "MANAGER REVIEW") {
        gate.classList.add("review");
        text.textContent = "REVIEW REQUIRED";
        icon.textContent = "⚠️";
    } else {
        gate.classList.add("locked");
        text.textContent = "LOCKED";
        icon.textContent = "🔒";
    }
}


function renderLiveState(state) {
    setCameraStatus(state.camera_running);

    if (!state.worker) {
        if (emptyWorkerState) {
            emptyWorkerState.hidden = false;
        }

        if (liveWorkerState) {
            liveWorkerState.hidden = true;
        }

        setGateState("ACCESS DENIED");
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

    setGateState(decision ? decision.status : "MANAGER REVIEW");
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
