
async function updateDashboard() {
    const connectionStatus = document.getElementById("connection-status");

    try {
        const response = await fetch("/api/monitoring", {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }



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


async function updateMetrics() {
    try {
        const response = await fetch("/api/metrics");

        if (!response.ok) {
            throw new Error("Failed to fetch reliability metrics");
        }

        const data = await response.json();

        document.getElementById("metric-failures").textContent =
            data.total_failures;

        document.getElementById("metric-trips").textContent =
            data.circuit_trips;

        document.getElementById("metric-recoveries").textContent =
            data.successful_recoveries;

        document.getElementById("metric-recovery-rate").textContent =
            `${data.recovery_rate}%`;

    } catch (error) {
        console.error("Metrics update failed:", error);
    }
}


let reliabilityChart = null;

async function updateReliabilityChart() {
    try {
        const response = await fetch("/api/metrics/trends");

        if (!response.ok) {
            throw new Error("Failed to fetch reliability trends");
        }

        const data = await response.json();
        const trends = data.trends;

        const labels = trends.map(day => day.date.slice(5));
        const failures = trends.map(day => day.failures);
        const trips = trends.map(day => day.circuit_trips);

        if (!reliabilityChart) {
            const canvas = document.getElementById("reliabilityChart");

            if (!canvas || typeof Chart === "undefined") {
                return;
            }

            reliabilityChart = new Chart(canvas, {
                type: "line",
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: "Database Failures",
                            data: failures,
                            borderColor: "#ef4444",
                            backgroundColor: "rgba(239, 68, 68, 0.1)",
                            tension: 0.3,
                            fill: true
                        },
                        {
                            label: "Circuit Breaker Trips",
                            data: trips,
                            borderColor: "#38bdf8",
                            backgroundColor: "rgba(56, 189, 248, 0.1)",
                            tension: 0.3,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: "#f8fafc"
                            }
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: "#94a3b8" },
                            grid: { color: "#334155" }
                        },
                        y: {
                            beginAtZero: true,
                            ticks: {
                                color: "#94a3b8",
                                precision: 0
                            },
                            grid: { color: "#334155" }
                        }
                    }
                }
            });
        } else {
            reliabilityChart.data.labels = labels;
            reliabilityChart.data.datasets[0].data = failures;
            reliabilityChart.data.datasets[1].data = trips;
            reliabilityChart.update();
        }

    } catch (error) {
        console.error("Reliability chart update failed:", error);
    }
}

updateReliabilityChart();
setInterval(updateReliabilityChart, 5000);


// Load metrics immediately.
updateMetrics();

// Refresh metrics every 2 seconds.
setInterval(updateMetrics, 2000);

updateIncidentTimeline();
setInterval(updateIncidentTimeline, 2000);

async function updateSystemHealth() {
    const indicator = document.getElementById("system-health");
    const label = document.getElementById("system-health-text");

    if (!indicator || !label) return;

    try {
        const response = await fetch("/health/ready", {
            cache: "no-store"
        });

        const data = await response.json();
        const status = data.system_status;

        console.log("FaultForge readiness:", {
            httpStatus: response.status,
            systemStatus: status,
            response: data
        });

        indicator.classList.remove(
            "health-healthy",
            "health-degraded",
            "health-unavailable",
            "health-unknown"
        );

        if (status === "healthy") {
            indicator.classList.add("health-healthy");
            label.textContent = "System Healthy";
        } else if (status === "degraded") {
            indicator.classList.add("health-degraded");
            label.textContent = "System Degraded";
        } else {
            indicator.classList.add("health-unavailable");
            label.textContent = "System Unavailable";
        }
    } catch (error) {
        indicator.classList.remove(
            "health-healthy",
            "health-degraded",
            "health-unavailable",
            "health-unknown"
        );

        indicator.classList.add("health-unknown");
        label.textContent = "Health Unknown";
        console.error("Health check failed:", error);
    }
}

updateSystemHealth();
setInterval(updateSystemHealth, 5000);