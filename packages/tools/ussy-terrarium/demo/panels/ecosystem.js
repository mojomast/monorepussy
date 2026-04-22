/**
 * Ecosystem Force-Graph Panel — D3.js v7 force-directed graph
 * Reads from ./fixtures/demo_health.json
 * Each node = module/file. Edges = shared territory_id clusters.
 */

const PALETTE = {
  thriving: "#4f98a3",
  healthy: "#e8af34",
  stressed: "#da7101",
  wilting: "#a12c7b",
  critical: "#6b0000",
  bg: "#171614",
  text: "#e8e6e3",
  edge: "rgba(79, 152, 163, 0.15)",
};

function healthColor(score) {
  if (score >= 0.8) return PALETTE.thriving;
  if (score >= 0.6) return PALETTE.healthy;
  if (score >= 0.4) return PALETTE.stressed;
  if (score >= 0.2) return PALETTE.wilting;
  return PALETTE.critical;
}

function healthLabel(score) {
  if (score >= 0.8) return "Thriving";
  if (score >= 0.6) return "Healthy";
  if (score >= 0.4) return "Stressed";
  if (score >= 0.2) return "Wilting";
  return "Critical";
}

function stageEmoji(stage) {
  if (stage === "pioneer") return "🌱";
  if (stage === "climax") return "🌳";
  return "🌿";
}

export async function initEcosystemPanel(containerSelector) {
  const container = document.querySelector(containerSelector);
  if (!container) return;

  const width = container.clientWidth;
  const height = Math.max(500, window.innerHeight * 0.6);

  container.style.width = "100%";
  container.style.height = height + "px";
  container.style.background = PALETTE.bg;
  container.style.borderRadius = "12px";
  container.style.overflow = "hidden";

  const svg = d3.select(container)
    .append("svg")
    .attr("viewBox", [0, 0, width, height])
    .attr("width", width)
    .attr("height", height)
    .style("display", "block");

  // Fetch data
  const response = await fetch("./fixtures/demo_health.json");
  const data = await response.json();

  // Build nodes and edges
  const nodes = [];
  const links = [];
  const territoryGroups = {};

  // Collect all states across adapters
  const allStates = new Map();
  for (const [adapterName, adapterData] of Object.entries(data.adapters)) {
    if (!adapterData.states) continue;
    for (const [path, state] of Object.entries(adapterData.states)) {
      if (!allStates.has(path)) {
        allStates.set(path, { ...state, path });
      } else {
        // Merge: take worst vitality
        const existing = allStates.get(path);
        existing.vitality = Math.min(existing.vitality, state.vitality);
        existing.crack_intensity = Math.max(existing.crack_intensity, state.crack_intensity || 0);
        if (state.infection_state && state.infection_state !== "S") {
          existing.infection_state = state.infection_state;
        }
        if (state.anomaly_active) existing.anomaly_active = true;
        existing.complexity_score = Math.max(existing.complexity_score || 0, state.complexity_score || 0);
        if (state.territory_id) existing.territory_id = state.territory_id;
        if (state.succession_stage && state.succession_stage !== "seral") {
          existing.succession_stage = state.succession_stage;
        }
      }
    }
  }

  for (const [path, state] of allStates) {
    const filename = path.split("/").pop();
    nodes.push({
      id: path,
      label: filename.length > 20 ? filename.slice(0, 17) + "..." : filename,
      fullPath: path,
      vitality: state.vitality || 0.5,
      crackIntensity: state.crack_intensity || 0,
      infectionState: state.infection_state || "S",
      anomalyActive: state.anomaly_active || false,
      complexityScore: state.complexity_score || 0,
      territoryId: state.territory_id || null,
      successionStage: state.succession_stage || "seral",
      radius: 6 + (state.complexity_score || 0) * 20,
    });

    if (state.territory_id) {
      if (!territoryGroups[state.territory_id]) {
        territoryGroups[state.territory_id] = [];
      }
      territoryGroups[state.territory_id].push(path);
    }
  }

  // Create edges between nodes sharing territory
  for (const [territory, paths] of Object.entries(territoryGroups)) {
    for (let i = 0; i < paths.length; i++) {
      for (let j = i + 1; j < paths.length; j++) {
        links.push({ source: paths[i], target: paths[j], territory });
      }
    }
  }

  // Simulation
  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(60))
    .force("charge", d3.forceManyBody().strength(-200))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide().radius(d => d.radius + 4));

  // Links
  const link = svg.append("g")
    .attr("stroke", PALETTE.edge)
    .attr("stroke-width", 1)
    .selectAll("line")
    .data(links)
    .join("line");

  // Nodes
  const node = svg.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .style("cursor", "pointer");

  // Node circles with radial bloom animation
  node.append("circle")
    .attr("r", 0)
    .attr("fill", d => healthColor(d.vitality))
    .attr("stroke", "#fff")
    .attr("stroke-width", 1.5)
    .attr("stroke-opacity", 0.3)
    .transition()
    .duration(800)
    .delay((d, i) => i * 30)
    .attr("r", d => d.radius);

  // Labels
  node.append("text")
    .text(d => d.label)
    .attr("x", d => d.radius + 4)
    .attr("y", 4)
    .attr("fill", PALETTE.text)
    .attr("font-size", "11px")
    .attr("font-family", "monospace")
    .attr("opacity", 0)
    .transition()
    .duration(600)
    .delay((d, i) => 600 + i * 20)
    .attr("opacity", 0.8);

  // Tooltip
  const tooltip = d3.select("body").append("div")
    .attr("class", "eco-tooltip")
    .style("position", "absolute")
    .style("visibility", "hidden")
    .style("background", "rgba(23, 22, 20, 0.95)")
    .style("color", PALETTE.text)
    .style("padding", "12px")
    .style("border-radius", "8px")
    .style("border", "1px solid rgba(79, 152, 163, 0.3)")
    .style("font-size", "13px")
    .style("font-family", "monospace")
    .style("pointer-events", "none")
    .style("z-index", "1000")
    .style("max-width", "280px");

  node.on("mouseover", (event, d) => {
    const dims = [
      { name: "Fatigue", score: 1 - d.crackIntensity },
      { name: "Epidemic", score: d.infectionState === "S" ? 1 : d.infectionState === "I" ? 0 : 0.5 },
      { name: "Anomaly", score: d.anomalyActive ? 0 : 1 },
      { name: "Complexity", score: 1 - d.complexityScore },
      { name: "Vitality", score: d.vitality },
    ];

    const bars = dims.map(dim => `
      <div style="display:flex;align-items:center;margin:3px 0;font-size:11px;">
        <span style="width:70px;">${dim.name}</span>
        <div style="flex:1;height:6px;background:rgba(255,255,255,0.1);border-radius:3px;margin:0 6px;">
          <div style="width:${(dim.score * 100).toFixed(0)}%;height:100%;background:${healthColor(dim.score)};border-radius:3px;"></div>
        </div>
        <span style="width:30px;text-align:right;">${(dim.score * 100).toFixed(0)}%</span>
      </div>
    `).join("");

    tooltip.html(`
      <div style="font-weight:bold;margin-bottom:6px;">${d.fullPath}</div>
      <div style="margin-bottom:8px;">
        <span style="font-size:18px;">${stageEmoji(d.successionStage)}</span>
        <span style="color:${healthColor(d.vitality)};font-weight:bold;">${(d.vitality * 100).toFixed(0)}%</span>
        <span style="opacity:0.7;">— ${healthLabel(d.vitality)}</span>
      </div>
      ${bars}
    `);
    tooltip.style("visibility", "visible");
  })
  .on("mousemove", (event) => {
    tooltip.style("top", (event.pageY + 12) + "px").style("left", (event.pageX + 12) + "px");
  })
  .on("mouseout", () => {
    tooltip.style("visibility", "hidden");
  })
  .on("click", (event, d) => {
    d.fx = d.fx ? null : d.x;
    d.fy = d.fy ? null : d.y;
    event.stopPropagation();
  });

  svg.on("click", () => {
    nodes.forEach(d => { d.fx = null; d.fy = null; });
  });

  // Drag behavior
  const drag = d3.drag()
    .on("start", (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    })
    .on("drag", (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on("end", (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
    });

  node.call(drag);

  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    node.attr("transform", d => `translate(${d.x},${d.y})`);
  });

  // Resize handler
  window.addEventListener("resize", () => {
    const newWidth = container.clientWidth;
    svg.attr("viewBox", [0, 0, newWidth, height]).attr("width", newWidth);
    simulation.force("center", d3.forceCenter(newWidth / 2, height / 2));
    simulation.alpha(0.3).restart();
  });
}
