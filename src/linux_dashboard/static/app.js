const ids = {
  host: document.querySelector("#host"),
  platform: document.querySelector("#platform"),
  updated: document.querySelector("#updated"),
  cpuPercent: document.querySelector("#cpu-percent"),
  cpuBar: document.querySelector("#cpu-bar"),
  cpuLoad: document.querySelector("#cpu-load"),
  cpuCores: document.querySelector("#cpu-cores"),
  cpuFreq: document.querySelector("#cpu-freq"),
  memPercent: document.querySelector("#mem-percent"),
  memBar: document.querySelector("#mem-bar"),
  memUsed: document.querySelector("#mem-used"),
  memFree: document.querySelector("#mem-free"),
  swapUsed: document.querySelector("#swap-used"),
  diskPercent: document.querySelector("#disk-percent"),
  diskBar: document.querySelector("#disk-bar"),
  diskUsed: document.querySelector("#disk-used"),
  diskTotal: document.querySelector("#disk-total"),
  diskCount: document.querySelector("#disk-count"),
  netTotal: document.querySelector("#net-total"),
  netRecv: document.querySelector("#net-recv"),
  netSent: document.querySelector("#net-sent"),
  netPackets: document.querySelector("#net-packets"),
  dockerStatus: document.querySelector("#docker-status"),
  dockerVersion: document.querySelector("#docker-version"),
  dockerRunning: document.querySelector("#docker-running"),
  dockerContainers: document.querySelector("#docker-containers"),
  dockerImages: document.querySelector("#docker-images"),
  dockerMessage: document.querySelector("#docker-message"),
  botStatus: document.querySelector("#bot-status"),
  botSummary: document.querySelector("#bot-summary"),
  botUpdated: document.querySelector("#bot-updated"),
  botAlerts: document.querySelector("#bot-alerts"),
  botStopped: document.querySelector("#bot-stopped"),
  ollamaStatus: document.querySelector("#ollama-status"),
  ollamaCli: document.querySelector("#ollama-cli"),
  ollamaServer: document.querySelector("#ollama-server"),
  ollamaVersion: document.querySelector("#ollama-version"),
  ollamaRequired: document.querySelector("#ollama-required"),
  ollamaBaseUrl: document.querySelector("#ollama-base-url"),
  ollamaModels: document.querySelector("#ollama-models"),
  ollamaMessage: document.querySelector("#ollama-message"),
  ollamaAnalyze: document.querySelector("#ollama-analyze"),
  ollamaAnalysis: document.querySelector("#ollama-analysis"),
  cpuChart: document.querySelector("#cpu-chart"),
  ramChart: document.querySelector("#ram-chart"),
  networkChart: document.querySelector("#network-chart"),
  cpuChartEmpty: document.querySelector("#cpu-chart-empty"),
  ramChartEmpty: document.querySelector("#ram-chart-empty"),
  networkChartEmpty: document.querySelector("#network-chart-empty"),
  cpuChartLatest: document.querySelector("#cpu-chart-latest"),
  ramChartLatest: document.querySelector("#ram-chart-latest"),
  netChartLatest: document.querySelector("#net-chart-latest"),
  diskChartLatest: document.querySelector("#disk-chart-latest"),
  diskGaugeFill: document.querySelector("#disk-gauge-fill"),
  diskGaugePercent: document.querySelector("#disk-gauge-percent"),
  diskGaugeDetail: document.querySelector("#disk-gauge-detail"),
  disks: document.querySelector("#disks"),
  processes: document.querySelector("#processes"),
};

const COLLECTING = "데이터 수집 중";
const config = window.dashboardConfig || {};
const refreshInterval = Number(config.refreshInterval || 1500);
const topProcesses = Number(config.topProcesses || 8);
let analyzing = false;
let analyzeTimer;

const hasNumber = (value) => Number.isFinite(Number(value));
const hasChart = () => typeof Chart !== "undefined";

const bytes = (value) => {
  if (!hasNumber(value)) return COLLECTING;
  const units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"];
  let size = Number(value);
  for (const unit of units) {
    if (size < 1024 || unit === "PiB") {
      return unit === "B" ? `${Math.round(size)} B` : `${size.toFixed(1)} ${unit}`;
    }
    size /= 1024;
  }
  return `${size.toFixed(1)} PiB`;
};

const throughput = (value) => `${bytes(value)}/s`;

const percentClass = (value) => {
  if (value >= 85) return "usage danger";
  if (value >= 70) return "usage warn";
  return "usage";
};

const percent = (value, digits = 1) => (hasNumber(value) ? `${Number(value).toFixed(digits)}%` : COLLECTING);

const row = (cells) => {
  const tr = document.createElement("tr");
  for (const cell of cells) {
    const td = document.createElement("td");
    if (typeof cell === "object") {
      td.textContent = cell.text;
      td.className = cell.className;
    } else {
      td.textContent = cell;
    }
    tr.append(td);
  }
  return tr;
};

const listItem = (text, className = "") => {
  const li = document.createElement("li");
  li.textContent = text;
  if (className) li.className = className;
  return li;
};

const renderDiskSummary = (disks) => {
  if (!Array.isArray(disks) || disks.length === 0) {
    ids.diskPercent.textContent = COLLECTING;
    ids.diskBar.style.width = "0";
    ids.diskUsed.textContent = COLLECTING;
    ids.diskTotal.textContent = COLLECTING;
    ids.diskCount.textContent = COLLECTING;
    return;
  }

  const total = disks.reduce((sum, disk) => sum + Number(disk.total || 0), 0);
  const used = disks.reduce((sum, disk) => sum + Number(disk.used || 0), 0);
  const usage = total > 0 ? (used / total) * 100 : null;

  ids.diskPercent.textContent = percent(usage, 0);
  ids.diskBar.style.width = `${Math.min(usage || 0, 100)}%`;
  ids.diskUsed.textContent = bytes(used);
  ids.diskTotal.textContent = bytes(total);
  ids.diskCount.textContent = `${disks.length.toLocaleString()}개`;
};

const renderDocker = (docker) => {
  if (!docker) {
    ids.dockerStatus.textContent = COLLECTING;
    ids.dockerStatus.className = "state-badge";
    ids.dockerMessage.textContent = COLLECTING;
    return;
  }

  const running = docker.status === "running";
  ids.dockerStatus.textContent = running ? "online" : "degraded";
  ids.dockerStatus.className = `state-badge ${running ? "ok" : "warn"}`;
  ids.dockerVersion.textContent = docker.version || COLLECTING;
  ids.dockerRunning.textContent = hasNumber(docker.containers_running)
    ? docker.containers_running.toLocaleString()
    : COLLECTING;
  ids.dockerContainers.textContent = hasNumber(docker.containers) ? docker.containers.toLocaleString() : COLLECTING;
  ids.dockerImages.textContent = hasNumber(docker.images) ? docker.images.toLocaleString() : COLLECTING;
  ids.dockerMessage.textContent = docker.message || COLLECTING;
};

const renderBot = (report) => {
  if (!report) {
    ids.botStatus.textContent = COLLECTING;
    ids.botStatus.className = "state-badge";
    ids.botSummary.textContent = COLLECTING;
    ids.botUpdated.textContent = COLLECTING;
    ids.botAlerts.replaceChildren(listItem(COLLECTING));
    ids.botStopped.replaceChildren(listItem(COLLECTING));
    return;
  }

  const status = report.status || "UNKNOWN";
  const statusClass = status === "OK" ? "ok" : status === "FAIL" ? "fail" : "warn";
  ids.botStatus.textContent = status.toLowerCase();
  ids.botStatus.className = `state-badge ${statusClass}`;
  ids.botSummary.textContent = report.summary || COLLECTING;
  ids.botUpdated.textContent = report.timestamp ? `checked ${new Date(report.timestamp).toLocaleTimeString()}` : COLLECTING;

  const alerts = Array.isArray(report.alerts) ? report.alerts : [];
  ids.botAlerts.replaceChildren(
    ...(alerts.length
      ? alerts.map((alert) => listItem(`${alert.level} ${alert.code}: ${alert.message}`, alert.level.toLowerCase()))
      : [listItem("OK monitored checks are within thresholds", "ok")]),
  );

  const stopped = Array.isArray(report.stopped_containers) ? report.stopped_containers : [];
  ids.botStopped.replaceChildren(
    ...(stopped.length
      ? stopped.map((container) =>
          listItem(`${container.name} · ${container.state} · ${container.status}`, "warn"),
        )
      : [listItem("OK no stopped containers detected", "ok")]),
  );
};

const renderOllama = (ollama) => {
  if (!ollama) {
    ids.ollamaStatus.textContent = COLLECTING;
    ids.ollamaStatus.className = "state-badge";
    ids.ollamaCli.textContent = COLLECTING;
    ids.ollamaServer.textContent = COLLECTING;
    ids.ollamaVersion.textContent = COLLECTING;
    ids.ollamaRequired.textContent = COLLECTING;
    ids.ollamaBaseUrl.textContent = COLLECTING;
    ids.ollamaModels.replaceChildren(listItem(COLLECTING));
    ids.ollamaMessage.textContent = COLLECTING;
    ids.ollamaAnalysis.textContent = COLLECTING;
    return;
  }

  const running = ollama.server_status === "running";
  const ready = running && Boolean(ollama.default_model_available);
  ids.ollamaStatus.textContent = ready ? "ready" : running ? "model missing" : "offline";
  ids.ollamaStatus.className = `state-badge ${ready ? "ok" : running ? "warn" : "fail"}`;
  ids.ollamaCli.textContent = ollama.cli_installed ? `installed${ollama.cli_path ? ` · ${ollama.cli_path}` : ""}` : "not found";
  ids.ollamaServer.textContent = ollama.server_status || COLLECTING;
  ids.ollamaVersion.textContent = ollama.version || COLLECTING;
  ids.ollamaRequired.textContent = `${ollama.default_model || "qwen2.5-coder:7b"} · ${
    ollama.default_model_available ? "available" : "missing"
  }`;
  ids.ollamaBaseUrl.textContent = ollama.base_url || COLLECTING;
  ids.ollamaMessage.textContent = ollama.message || COLLECTING;
  ids.ollamaAnalyze.disabled = !ready || analyzing;
  ids.ollamaAnalyze.title = ready ? "" : `Install model with: ollama run ${ollama.default_model || "qwen2.5-coder:7b"}`;

  const models = Array.isArray(ollama.models) ? ollama.models : [];
  ids.ollamaModels.replaceChildren(
    ...(models.length
      ? models.map((model) =>
          listItem(model, model === ollama.default_model || model.startsWith(`${ollama.default_model}:`) ? "ok" : ""),
        )
      : [listItem("No models reported", running ? "warn" : "fail")]),
  );
};

const analyzeSystem = async () => {
  if (analyzing) return;
  analyzing = true;
  ids.ollamaAnalyze.disabled = true;
  const startedAt = Date.now();
  ids.ollamaAnalysis.textContent = "분석 중... 0s";
  analyzeTimer = window.setInterval(() => {
    const seconds = Math.floor((Date.now() - startedAt) / 1000);
    ids.ollamaAnalysis.textContent = `분석 중... ${seconds}s\n14B 모델은 CPU 환경에서 시간이 걸릴 수 있습니다.`;
  }, 1000);
  try {
    const response = await fetch("/api/ollama/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    if (!data.ok) {
      ids.ollamaAnalysis.textContent = data.hint ? `${data.error}\n${data.hint}` : data.error || "Analysis failed";
      return;
    }
    ids.ollamaAnalysis.textContent = data.analysis || "No analysis returned.";
  } catch (error) {
    ids.ollamaAnalysis.textContent = `Analysis failed: ${error.message}`;
  } finally {
    window.clearInterval(analyzeTimer);
    analyzing = false;
    ids.ollamaAnalyze.disabled = false;
  }
};

let cpuChart;
let ramChart;
let networkChart;

const chartTextColor = "#82918d";
const chartGridColor = "rgba(50, 246, 164, 0.11)";

const chartOptions = (suffix, suggestedMax = 100) => ({
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  interaction: {
    intersect: false,
    mode: "index",
  },
  plugins: {
    legend: {
      labels: {
        color: chartTextColor,
        boxWidth: 10,
        font: {
          family: "'JetBrains Mono', Consolas, monospace",
          size: 11,
        },
      },
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          const value = Number(context.parsed.y || 0);
          return `${context.dataset.label}: ${suffix === "/s" ? throughput(value) : `${value.toFixed(1)}${suffix}`}`;
        },
      },
    },
  },
  scales: {
    x: {
      ticks: {
        color: chartTextColor,
        maxRotation: 0,
        autoSkip: true,
        maxTicksLimit: 6,
      },
      grid: {
        color: "rgba(130, 145, 141, 0.08)",
      },
    },
    y: {
      beginAtZero: true,
      suggestedMax,
      ticks: {
        color: chartTextColor,
        callback: (value) => (suffix === "/s" ? throughput(value) : `${value}${suffix}`),
      },
      grid: {
        color: chartGridColor,
      },
    },
  },
});

const makeChart = (canvas, datasets, options) =>
  new Chart(canvas, {
    type: "line",
    data: {
      labels: [],
      datasets,
    },
    options,
  });

const ensureCharts = () => {
  if (!hasChart() || cpuChart || !ids.cpuChart || !ids.ramChart || !ids.networkChart) return;

  cpuChart = makeChart(
    ids.cpuChart,
    [
      {
        label: "CPU",
        data: [],
        borderColor: "#32f6a4",
        backgroundColor: "rgba(50, 246, 164, 0.12)",
        fill: true,
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.28,
      },
    ],
    chartOptions("%"),
  );

  ramChart = makeChart(
    ids.ramChart,
    [
      {
        label: "RAM",
        data: [],
        borderColor: "#75d7ff",
        backgroundColor: "rgba(117, 215, 255, 0.12)",
        fill: true,
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.28,
      },
    ],
    chartOptions("%"),
  );

  networkChart = makeChart(
    ids.networkChart,
    [
      {
        label: "RX",
        data: [],
        borderColor: "#32f6a4",
        backgroundColor: "rgba(50, 246, 164, 0.08)",
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.28,
      },
      {
        label: "TX",
        data: [],
        borderColor: "#f4bd4f",
        backgroundColor: "rgba(244, 189, 79, 0.08)",
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.28,
      },
    ],
    chartOptions("/s", 1024),
  );
};

const setEmpty = (element, visible) => {
  if (!element) return;
  element.hidden = !visible;
};

const labels = (history) => history.map((item) => new Date(item.timestamp).toLocaleTimeString());

const updateChart = (chart, emptyElement, history, datasets) => {
  const hasData = hasChart() && chart && Array.isArray(history) && history.length >= 2;
  setEmpty(emptyElement, !hasData);
  if (!hasData) return;

  chart.data.labels = labels(history);
  datasets.forEach((values, index) => {
    chart.data.datasets[index].data = values;
  });
  chart.update("none");
};

const renderCharts = (history) => {
  ensureCharts();
  const samples = Array.isArray(history) ? history : [];
  const latest = samples.at(-1);

  ids.cpuChartLatest.textContent = latest && hasNumber(latest.cpu_percent) ? percent(latest.cpu_percent) : COLLECTING;
  ids.ramChartLatest.textContent = latest && hasNumber(latest.memory_percent) ? percent(latest.memory_percent) : COLLECTING;
  ids.netChartLatest.textContent =
    latest && hasNumber(latest.recv_rate) && hasNumber(latest.sent_rate)
      ? `RX ${throughput(latest.recv_rate)} · TX ${throughput(latest.sent_rate)}`
      : COLLECTING;
  ids.diskChartLatest.textContent = latest && hasNumber(latest.disk_percent) ? percent(latest.disk_percent, 0) : COLLECTING;

  updateChart(
    cpuChart,
    ids.cpuChartEmpty,
    samples,
    [samples.map((item) => Number(item.cpu_percent || 0))],
  );
  updateChart(
    ramChart,
    ids.ramChartEmpty,
    samples,
    [samples.map((item) => Number(item.memory_percent || 0))],
  );
  updateChart(networkChart, ids.networkChartEmpty, samples, [
    samples.map((item) => Number(item.recv_rate || 0)),
    samples.map((item) => Number(item.sent_rate || 0)),
  ]);
};

const renderDiskGauge = (disks) => {
  if (!Array.isArray(disks) || disks.length === 0) {
    ids.diskGaugeFill.style.width = "0";
    ids.diskGaugePercent.textContent = COLLECTING;
    ids.diskGaugeDetail.textContent = COLLECTING;
    return;
  }

  const total = disks.reduce((sum, disk) => sum + Number(disk.total || 0), 0);
  const used = disks.reduce((sum, disk) => sum + Number(disk.used || 0), 0);
  const usage = total > 0 ? (used / total) * 100 : null;
  ids.diskGaugeFill.style.width = `${Math.min(usage || 0, 100)}%`;
  ids.diskGaugePercent.textContent = percent(usage, 0);
  ids.diskGaugeDetail.textContent = `${bytes(used)} used / ${bytes(total)} total`;
};

const render = (data) => {
  ids.host.textContent = data.hostname || COLLECTING;
  ids.platform.textContent = data.platform
    ? `${data.platform} · uptime ${Math.floor(data.uptime_seconds / 3600)}h ${Math.floor((data.uptime_seconds % 3600) / 60)}m`
    : COLLECTING;
  ids.updated.textContent = `updated ${new Date(data.timestamp).toLocaleTimeString()}`;

  ids.cpuPercent.textContent = percent(data.cpu.percent);
  ids.cpuBar.style.width = `${Math.min(data.cpu.percent || 0, 100)}%`;
  ids.cpuLoad.textContent = data.cpu.load_avg ? data.cpu.load_avg.map((item) => item.toFixed(2)).join(" / ") : COLLECTING;
  ids.cpuCores.textContent = hasNumber(data.cpu.cores_logical)
    ? `${data.cpu.cores_physical ?? "?"} physical / ${data.cpu.cores_logical} logical`
    : COLLECTING;
  ids.cpuFreq.textContent = data.cpu.frequency_mhz ? `${data.cpu.frequency_mhz.toFixed(0)} MHz` : COLLECTING;

  ids.memPercent.textContent = percent(data.memory.percent);
  ids.memBar.style.width = `${Math.min(data.memory.percent || 0, 100)}%`;
  ids.memUsed.textContent = `${bytes(data.memory.used)} / ${bytes(data.memory.total)}`;
  ids.memFree.textContent = bytes(data.memory.available);
  ids.swapUsed.textContent = `${bytes(data.memory.swap_used)} / ${bytes(data.memory.swap_total)}`;

  renderDiskSummary(data.disks);
  renderDiskGauge(data.disks);

  ids.netRecv.textContent = bytes(data.network.bytes_recv);
  ids.netSent.textContent = bytes(data.network.bytes_sent);
  ids.netTotal.textContent = bytes(data.network.bytes_recv + data.network.bytes_sent);
  ids.netPackets.textContent =
    hasNumber(data.network.packets_recv) && hasNumber(data.network.packets_sent)
      ? `${data.network.packets_recv.toLocaleString()} / ${data.network.packets_sent.toLocaleString()}`
      : COLLECTING;

  renderDocker(data.docker);

  ids.disks.replaceChildren(
    ...(data.disks || []).slice(0, 10).map((disk) =>
      row([
        disk.mountpoint,
        disk.fstype,
        bytes(disk.used),
        bytes(disk.total),
        { text: `${disk.percent.toFixed(0)}%`, className: percentClass(disk.percent) },
      ]),
    ),
  );

  ids.processes.replaceChildren(
    ...(data.processes || []).map((process) =>
      row([
        String(process.pid),
        process.name,
        process.username,
        `${process.cpu_percent.toFixed(1)}%`,
        `${process.memory_percent.toFixed(1)}%`,
      ]),
    ),
  );
};

const renderMetrics = (payload) => {
  render(payload.current);
  renderCharts(payload.history);
  renderBot(payload.alerts);
  renderOllama(payload.ollama);
};

const refresh = async () => {
  const response = await fetch(`/api/metrics?top=${topProcesses}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  renderMetrics(await response.json());
};

refresh().catch((error) => {
  ids.updated.textContent = error.message;
});
setInterval(() => {
  refresh().catch((error) => {
    ids.updated.textContent = `refresh failed: ${error.message}`;
  });
}, refreshInterval);

ids.ollamaAnalyze?.addEventListener("click", () => {
  analyzeSystem();
});
