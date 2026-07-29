console.log("SafeGate AI frontend loaded successfully.");
console.log("SafeGate AI frontend loaded successfully.");

const startButton = document.getElementById(
    "start-camera-button"
);

const stopButton = document.getElementById(
    "stop-camera-button"
);

const cameraFeed = document.getElementById(
    "live-camera-feed"
);

const cameraStatusBadge = document.getElementById(
    "camera-status-badge"
);


function setCameraStatus(isRunning) {
    if (!cameraStatusBadge) {
        return;
    }

    cameraStatusBadge.innerHTML = isRunning
        ? `
            <span class="status-dot online"></span>
            Live
        `
        : `
            <span class="status-dot warning"></span>
            Stopped
        `;

    if (startButton) {
        startButton.disabled = isRunning;
    }

    if (stopButton) {
        stopButton.disabled = !isRunning;
    }
}


async function checkCameraStatus() {
    try {
        const response = await fetch("/camera/status");
        const data = await response.json();

        setCameraStatus(data.camera_running);
    } catch (error) {
        console.error(
            "Could not check camera status:",
            error
        );
    }
}


async function startCamera() {
    try {
        const response = await fetch(
            "/camera/start",
            {
                method: "POST",
            }
        );

        const data = await response.json();

        if (cameraFeed) {
            cameraFeed.src =
                `/video-feed?timestamp=${Date.now()}`;
        }

        setCameraStatus(data.camera_running);
    } catch (error) {
        console.error(
            "Could not start camera:",
            error
        );
    }
}


async function stopCamera() {
    try {
        const response = await fetch(
            "/camera/stop",
            {
                method: "POST",
            }
        );

        const data = await response.json();

        if (cameraFeed) {
            cameraFeed.removeAttribute("src");
        }

        setCameraStatus(data.camera_running);
    } catch (error) {
        console.error(
            "Could not stop camera:",
            error
        );
    }
}


if (startButton) {
    startButton.addEventListener(
        "click",
        startCamera
    );
}

if (stopButton) {
    stopButton.addEventListener(
        "click",
        stopCamera
    );
}

checkCameraStatus();