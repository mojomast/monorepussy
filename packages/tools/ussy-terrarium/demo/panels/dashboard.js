/**
 * Dashboard Panel — Animated health score dashboard
 * Reads from ./fixtures/demo_health.json
 * Mirrors the Rich terminal dashboard output.
 */

const PALETTE = {
  thriving: "#4f98a3",
  healthy: "#e8af34",
  stressed: "#da7101",
  wilting: "#a12c7b",
  critical: "#6b0000",
};

function statusLabel(score) {
  if (score >= 0.8) return "Thriving";
  if (score >= 0.6) return "Healthy";
  if (score >= 0.4) return "Stressed";
  if (score >= 0.2) return "Wilting";
  return "Critical";
}

function statusColor(score) {
  if (score >= 0.8) return PALETTE.thriving;
  if (score >= 0.6) return PALETTE.healthy;
  if (score >= 0.4) return PALETTE.stressed;
  if (score >= 0.2) return PALETTE.wilting;
  return PALETTE.critical;
}

export async function initDashboardPanel(containerSelector) {
  const container = document.querySelector(containerSelector);
  if (!container) return;

  const response = await fetch("./fixtures/demo_health.json");
  const data = await response.json();
  const health = data.health;

  const dimensions = [
    { key: "overall", name: "Overall", weight: null },
    { key: "fatigue", name: "Fatigue", weight: 0.20 },
    { key: "epidemic", name: "Epidemic", weight: 0.20 },
    { key: "anomaly", name: "Anomaly", weight: 0.20 },
    { key: "drift", name: "Drift", weight: 0.15 },
    { key: "churn", name: "Churn", weight: 0.10 },
    { key: "complexity", name: "Complexity", weight: 0.15 },
  ];

  const isDark = document.documentElement.classList.contains("dark") ||
    (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);

  const bgColor = isDark ? "rgba(23, 22, 20, 0.8)" : "rgba(255, 255, 255, 0.9)";
  const textColor = isDark ? "#e8e6e3" : "#171614";
  const borderColor = isDark ? "rgba(79, 152, 163, 0.2)" : "rgba(79, 152, 163, 0.3)";

  container.style.background = bgColor;
  container.style.color = textColor;
  container.style.borderRadius = "12px";
  container.style.padding = "24px";
  container.style.border = `1px solid ${borderColor}`;
  container.style.backdropFilter = "blur(10px)";

  const header = document.createElement("div");
  header.style.marginBottom = "20px";
  header.innerHTML = `
    <div style="font-family: monospace; font-size: 14px; color: ${PALETTE.thriving}; text-shadow: 0 0 10px rgba(79, 152, 163, 0.3); margin-bottom: 4px;">
      🌿 Terrarium Ecosystem Dashboard
    </div>
    <div style="font-size: 12px; opacity: 0.6;">Real-time health scoring across 6 dimensions</div>
  `;
  container.appendChild(header);

  dimensions.forEach((dim, index) => {
    const score = health[dim.key];
    const pct = (score * 100).toFixed(1);
    const color = statusColor(score);
    const label = statusLabel(score);
    const isUrgent = score < 0.4;

    const row = document.createElement("div");
    row.style.marginBottom = "14px";
    row.style.opacity = "0";
    row.style.transform = "translateY(8px)";
    row.style.transition = `opacity 0.5s ease ${index * 0.1}s, transform 0.5s ease ${index * 0.1}s`;

    row.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <span style="font-weight: ${dim.key === "overall" ? "bold" : "normal"}; font-size: ${dim.key === "overall" ? "15px" : "13px"};">
          ${dim.name}
          ${dim.weight ? `<span style="opacity: 0.5; font-size: 11px;">(${dim.weight})</span>` : ""}
        </span>
        <span style="font-family: monospace; font-size: 13px;">
          <span style="color: ${color}; font-weight: bold;">${pct}%</span>
          <span style="opacity: 0.6; font-size: 11px; margin-left: 6px;">${label}</span>
        </span>
      </div>
      <div style="width: 100%; height: 8px; background: ${isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.08)"}; border-radius: 4px; overflow: hidden;">
        <div class="dash-bar ${isUrgent ? "urgent" : ""}" 
             data-width="${pct}%"
             style="width: 0%; height: 100%; background: ${color}; border-radius: 4px; transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1) ${index * 0.1 + 0.3}s;">
        </div>
      </div>
    `;

    container.appendChild(row);

    // Animate in
    requestAnimationFrame(() => {
      row.style.opacity = "1";
      row.style.transform = "translateY(0)";
    });
  });

  // Footer metadata
  const footer = document.createElement("div");
  footer.style.marginTop = "20px";
  footer.style.paddingTop = "16px";
  footer.style.borderTop = `1px solid ${borderColor}`;
  footer.style.display = "flex";
  footer.style.gap = "12px";
  footer.style.flexWrap = "wrap";

  const pills = [
    { label: "Territory", value: health.territory || "N/A" },
    { label: "Succession", value: health.succession || "seral" },
  ];

  pills.forEach(pill => {
    const el = document.createElement("span");
    el.style.padding = "4px 12px";
    el.style.borderRadius = "20px";
    el.style.fontSize = "12px";
    el.style.background = isDark ? "rgba(79, 152, 163, 0.1)" : "rgba(79, 152, 163, 0.08)";
    el.style.color = PALETTE.thriving;
    el.style.border = `1px solid ${borderColor}`;
    el.textContent = `${pill.label}: ${pill.value}`;
    footer.appendChild(el);
  });

  container.appendChild(footer);

  // Trigger bar animations after DOM insertion
  requestAnimationFrame(() => {
    container.querySelectorAll(".dash-bar").forEach(bar => {
      bar.style.width = bar.dataset.width;
    });
  });

  // Add urgent pulse animation style
  if (!document.getElementById("dash-urgent-style")) {
    const style = document.createElement("style");
    style.id = "dash-urgent-style";
    style.textContent = `
      @keyframes dash-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
      }
      .dash-bar.urgent {
        animation: dash-pulse 1.5s ease-in-out infinite;
      }
      @media (prefers-reduced-motion: reduce) {
        .dash-bar.urgent { animation: none; }
      }
    `;
    document.head.appendChild(style);
  }
}
