/**
 * Seasons Timeline Panel — Chart.js v4 animated line chart
 * Shows synthetic ecosystem health evolution over 6 months.
 */

const PALETTE = {
  overall: "#4f98a3",
  fatigue: "#e8af34",
  epidemic: "#da7101",
  complexity: "#a12c7b",
  grid: "rgba(79, 152, 163, 0.1)",
  text: "#e8e6e3",
};

export async function initSeasonsPanel(containerSelector) {
  const container = document.querySelector(containerSelector);
  if (!container) return;

  const response = await fetch("./fixtures/demo_health.json");
  const data = await response.json();
  const baseline = data.health;

  // Generate 6 months of synthetic data with realistic deltas
  const months = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"];
  
  // Start from slightly different baselines and apply trends
  const datasets = [
    {
      label: "Overall",
      key: "overall",
      color: PALETTE.overall,
      data: generateTrend(baseline.overall, [0.02, -0.03, -0.05, -0.02, 0.04, 0.06]),
    },
    {
      label: "Fatigue",
      key: "fatigue",
      color: PALETTE.fatigue,
      data: generateTrend(baseline.fatigue, [0.05, -0.08, -0.12, -0.05, 0.03, 0.08]),
    },
    {
      label: "Epidemic",
      key: "epidemic",
      color: PALETTE.epidemic,
      data: generateTrend(baseline.epidemic, [-0.02, -0.15, -0.20, -0.10, 0.05, 0.12]),
    },
    {
      label: "Complexity",
      key: "complexity",
      color: PALETTE.complexity,
      data: generateTrend(baseline.complexity, [0.03, -0.05, -0.08, -0.03, 0.02, 0.05]),
    },
  ];

  // Find the lowest point for annotation
  let minValue = 1;
  let minMonth = 0;
  datasets.forEach(ds => {
    ds.data.forEach((v, i) => {
      if (v < minValue) {
        minValue = v;
        minMonth = i;
      }
    });
  });

  const isDark = document.documentElement.classList.contains("dark") ||
    (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches);

  const bgColor = isDark ? "rgba(23, 22, 20, 0.8)" : "rgba(255, 255, 255, 0.9)";
  const textColor = isDark ? "#e8e6e3" : "#171614";
  const gridColor = isDark ? PALETTE.grid : "rgba(0, 0, 0, 0.08)";
  const borderColor = isDark ? "rgba(79, 152, 163, 0.2)" : "rgba(79, 152, 163, 0.3)";

  container.style.background = bgColor;
  container.style.borderRadius = "12px";
  container.style.padding = "24px";
  container.style.border = `1px solid ${borderColor}`;
  container.style.backdropFilter = "blur(10px)";

  const canvas = document.createElement("canvas");
  canvas.style.width = "100%";
  canvas.style.height = "300px";
  container.appendChild(canvas);

  const ctx = canvas.getContext("2d");

  new Chart(ctx, {
    type: "line",
    data: {
      labels: months,
      datasets: datasets.map(ds => ({
        label: ds.label,
        data: ds.data.map(v => v * 100),
        borderColor: ds.color,
        backgroundColor: ds.color + "20",
        borderWidth: 2,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBackgroundColor: ds.color,
        fill: false,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 2000,
        easing: "easeOutQuart",
        x: {
          from: 0,
        },
      },
      interaction: {
        mode: "index",
        intersect: false,
      },
      plugins: {
        legend: {
          position: "top",
          align: "end",
          labels: {
            color: textColor,
            font: { family: "monospace", size: 11 },
            usePointStyle: true,
            pointStyle: "circle",
            padding: 16,
          },
        },
        annotation: {
          annotations: {
            highChurnEvent: {
              type: "label",
              xValue: minMonth,
              yValue: minValue * 100,
              backgroundColor: "rgba(107, 0, 0, 0.8)",
              color: "#fff",
              content: "High Churn Event",
              font: { family: "monospace", size: 11 },
              padding: 6,
              borderRadius: 4,
              yAdjust: -20,
            },
            line1: {
              type: "line",
              xMin: minMonth,
              xMax: minMonth,
              borderColor: "rgba(107, 0, 0, 0.4)",
              borderWidth: 1,
              borderDash: [4, 4],
            },
          },
        },
        tooltip: {
          backgroundColor: "rgba(23, 22, 20, 0.95)",
          titleColor: textColor,
          bodyColor: textColor,
          borderColor: borderColor,
          borderWidth: 1,
          titleFont: { family: "monospace" },
          bodyFont: { family: "monospace" },
          padding: 12,
          callbacks: {
            label: (context) => {
              return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            font: { family: "monospace", size: 11 },
          },
        },
        y: {
          min: 0,
          max: 100,
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            font: { family: "monospace", size: 11 },
            callback: (value) => value + "%",
          },
          title: {
            display: true,
            text: "Health Score",
            color: textColor,
            font: { family: "monospace", size: 11 },
          },
        },
      },
    },
  });
}

function generateTrend(base, deltas) {
  let current = base;
  return deltas.map(delta => {
    current = Math.max(0, Math.min(1, current + delta));
    return current;
  });
}
