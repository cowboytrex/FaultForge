
async function updateDashboard() {
    const connectionStatus = document.getElementById("connection-status");

    try {
        const response = await fetch("/api/monitoring", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const breaker = data.circuit_breaker;

        // Update circuit breaker state
        const stateElement = document.getElementById("breaker-state");

        stateElement.textContent = breaker.state;

        stateElement.classList.remove(
            "state-closed",
            "state-open",
            "state-half-open"
        );

        if (breaker.state === "CLOSED") {
            stateElement.classList.add("state-closed");
        } else if (breaker.state === "OPEN") {
            stateElement.classList.add("state-open");
        } else if (breaker.state === "HALF_OPEN") {
            stateElement.classList.add("state-half-open");
        }

        // Update circuit breaker metrics
        document.getElementById("failure-count").textContent =
            breaker.failure_count;

        document.getElementById("failure-threshold").textContent =
            breaker.failure_threshold;

        document.getElementById("recovery-timeout").textContent =
            breaker.recovery_timeout;

        // Update recovery countdown
        const recoveryContainer =
            document.getElementById("recovery-container");

        const recoveryCountdown =
            document.getElementById("recovery-countdown");

        const recoveryProgressBar =
            document.getElementById("recovery-progress-bar");

        if (breaker.state === "OPEN") {
            recoveryContainer.style.display = "block";

            const remaining = Number(breaker.recovery_remaining ?? 0);
            const timeout = Number(breaker.recovery_timeout);

            recoveryCountdown.textContent =
                remaining > 0
                    ? `${remaining.toFixed(1)}s`
                    : "Ready to test recovery";

            const progress = timeout > 0
                ? ((timeout - remaining) / timeout) * 100
                : 100;

            recoveryProgressBar.style.width =
                `${Math.min(100, Math.max(0, progress))}%`;
        } else {
            recoveryContainer.style.display = "none";
        }

        connectionStatus.textContent = "Monitoring API connected";

    } catch (error) {
        connectionStatus.textContent = "Monitoring API unavailable";
        document.getElementById("breaker-state").textContent = "UNKNOWN";
        console.error("Dashboard update failed:", error);
    }
}


// Fault injection button
const failureButton = document.getElementById("simulate-failure-btn");
const simulationResult = document.getElementById("simulation-result");

failureButton.addEventListener("click", async () => {
    failureButton.disabled = true;
    simulationResult.textContent = "Simulating database failure...";

    try {
        const response = await fetch("/api/simulate-failure", {
            method: "POST"
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const breaker = data.circuit_breaker;

        simulationResult.textContent =
            `Failure count: ${breaker.failure_count} | State: ${breaker.state}`;

        await updateDashboard();

    } catch (error) {
        simulationResult.textContent =
            "Simulation failed. Check the Flask server.";

        console.error("Fault injection failed:", error);

    } finally {
        failureButton.disabled = false;
    }
});


// Database recovery button
const recoveryButton = document.getElementById("test-recovery-btn");

recoveryButton.addEventListener("click", async () => {
    recoveryButton.disabled = true;
    simulationResult.textContent = "Testing database recovery...";

    try {
        const response = await fetch("/api/services", {
            cache: "no-store"
        });

        if (!response.ok && response.status !== 503) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        await updateDashboard();

        if (data.source === "primary") {
            simulationResult.textContent =
                "Recovery successful! PostgreSQL is serving requests.";
        } else if (data.source === "cache") {
            simulationResult.textContent =
                "Recovery not completed. Redis fallback is active.";
        } else {
            simulationResult.textContent =
                "Recovery failed. Check the backend service.";
        }

    } catch (error) {
        simulationResult.textContent = "Recovery request failed.";
        console.error("Recovery test failed:", error);

    } finally {
        recoveryButton.disabled = false;
    }
});


// Start monitoring
updateDashboard();
setInterval(updateDashboard, 2000);


async function updateIncidentTimeline() {
    const timeline = document.getElementById("incident-timeline");

    try {
        const response = await fetch("/api/events", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const events = data.events;

        timeline.replaceChildren();

        if (events.length === 0) {
            const emptyMessage = document.createElement("p");
            emptyMessage.textContent = "No incidents recorded yet.";
            timeline.appendChild(emptyMessage);
            return;
        }

        for (const event of events) {
            const item = document.createElement("div");
            item.className = `incident-event severity-${event.severity}`;

            const title = document.createElement("strong");
            title.textContent = event.type.replaceAll("_", " ").toUpperCase();

            const message = document.createElement("p");
            message.textContent = event.message;

            const timestamp = document.createElement("small");
            timestamp.textContent =
                new Date(event.timestamp).toLocaleString();

            item.append(title, message, timestamp);
            timeline.appendChild(item);
        }

    } catch (error) {
        console.error("Incident timeline update failed:", error);
        timeline.textContent = "Unable to load incident events.";
    }
}

updateIncidentTimeline();
setInterval(updateIncidentTimeline, 2000);
