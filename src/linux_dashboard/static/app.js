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
  netTotal: document.querySelector("#net-total"),
  netRecv: document.querySelector("#net-recv"),
  netSent: document.querySelector("#net-sent"),
  netPackets: document.querySelector("#net-packets"),
  disks: document.querySelector("#disks"),
  processes: document.querySelector("#processes"),
};

const bytes = (value) => {
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

const percentClass = (value) => {
  if (value >= 85) return "usage danger";
  if (value >= 70) return "usage warn";
  return "usage";
};

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

const render = (data) => {
  ids.host.textContent = data.hostname;
  ids.platform.textContent = `${data.platform} · uptime ${Math.floor(data.uptime_seconds / 3600)}h ${Math.floor((data.uptime_seconds % 3600) / 60)}m`;
  ids.updated.textContent = new Date(data.timestamp).toLocaleTimeString();

  ids.cpuPercent.textContent = `${data.cpu.percent.toFixed(1)}%`;
  ids.cpuBar.style.width = `${Math.min(data.cpu.percent, 100)}%`;
  ids.cpuLoad.textContent = data.cpu.load_avg ? data.cpu.load_avg.map((item) => item.toFixed(2)).join(" / ") : "n/a";
  ids.cpuCores.textContent = `${data.cpu.cores_physical ?? "?"} physical / ${data.cpu.cores_logical} logical`;
  ids.cpuFreq.textContent = data.cpu.frequency_mhz ? `${data.cpu.frequency_mhz.toFixed(0)} MHz` : "n/a";

  ids.memPercent.textContent = `${data.memory.percent.toFixed(1)}%`;
  ids.memBar.style.width = `${Math.min(data.memory.percent, 100)}%`;
  ids.memUsed.textContent = `${bytes(data.memory.used)} / ${bytes(data.memory.total)}`;
  ids.memFree.textContent = bytes(data.memory.available);
  ids.swapUsed.textContent = `${bytes(data.memory.swap_used)} / ${bytes(data.memory.swap_total)}`;

  ids.netRecv.textContent = bytes(data.network.bytes_recv);
  ids.netSent.textContent = bytes(data.network.bytes_sent);
  ids.netTotal.textContent = bytes(data.network.bytes_recv + data.network.bytes_sent);
  ids.netPackets.textContent = `${data.network.packets_recv.toLocaleString()} / ${data.network.packets_sent.toLocaleString()}`;

  ids.disks.replaceChildren(
    ...data.disks.slice(0, 10).map((disk) =>
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
    ...data.processes.map((process) =>
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

const refresh = async () => {
  const response = await fetch("/api/snapshot?top=8", { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  render(await response.json());
};

refresh();
setInterval(() => {
  refresh().catch((error) => {
    ids.updated.textContent = error.message;
  });
}, 1500);
