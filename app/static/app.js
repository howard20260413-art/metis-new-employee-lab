const canvas = document.getElementById("office-canvas");
const ctx = canvas.getContext("2d");

// 簡易辦公室網格地圖物件
const player = { x: 80, y: 210, r: 14, speed: 18 };
const objects = [
  { id: "door", label: "打卡門禁", x: 70, y: 80, w: 60, h: 40, color: "#93c5fd", msg: "【門禁系統】請開啟 PDA 終端機執行 whoami 與 pwd 完成上班打卡。" },
  { id: "pc", label: "辦公電腦", x: 230, y: 180, w: 70, h: 50, color: "#86efac", msg: "已連線至辦公室工作站，按 E 開啟 METIS-PDA。" },
  { id: "boss", label: "部門主管", x: 400, y: 120, w: 50, h: 50, color: "#fca5a5", msg: "【部門主管】請先完成日常 10 項基礎與維運任務，再來找我進行定期考核！" }
];

let latestState = null;

function drawMap() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  // 網格線
  ctx.strokeStyle = "#e5e7eb";
  for (let x = 0; x < canvas.width; x += 40) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
  }
  for (let y = 0; y < canvas.height; y += 40) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
  }
  // 繪製互動物件
  objects.forEach(obj => {
    if (obj.id === "boss" && (!latestState || !latestState.stage3_unlocked)) return;
    ctx.fillStyle = obj.color;
    ctx.fillRect(obj.x, obj.y, obj.w, obj.h);
    ctx.strokeStyle = "#374151";
    ctx.strokeRect(obj.x, obj.y, obj.w, obj.h);
    ctx.fillStyle = "#111827";
    ctx.font = "12px sans-serif";
    ctx.fillText(obj.label, obj.x + 6, obj.y + 28);
  });
  // 繪製玩家
  ctx.beginPath();
  ctx.arc(player.x, player.y, player.r, 0, Math.PI * 2);
  ctx.fillStyle = "#111827";
  ctx.fill();
  ctx.strokeStyle = "#dc2626";
  ctx.lineWidth = 3;
  ctx.stroke();
  ctx.lineWidth = 1;
}

function getNearObject() {
  return objects.find(obj => {
    if (obj.id === "boss" && (!latestState || !latestState.stage3_unlocked)) return false;
    const cx = obj.x + obj.w / 2;
    const cy = obj.y + obj.h / 2;
    return Math.hypot(player.x - cx, player.y - cy) < 65;
  });
}

function interact() {
  const near = getNearObject();
  if (!near) return;
  document.getElementById("npc-title").textContent = near.label;
  if (near.id === "pc") {
    openPda();
  } else if (near.id === "boss") {
    if (latestState && latestState.stage3_done) {
      document.getElementById("npc-text").textContent =
        "【部門主管】幹得好！系統異常已排除，請查看 secret/.intruder_manifest.txt 內的聲明 Flag 並提交至平台！";
    } else {
      document.getElementById("npc-text").textContent =
        "【部門主管・緊急任務】系統剛才遭到異常竄改！請檢查日誌線索、終止異常進程、將設定檔 PORT 復原為 8080，並把入侵者留下的隱藏機密檔權限收斂為 600！";
    }
  } else {
    document.getElementById("npc-text").textContent = near.msg;
  }
}

window.addEventListener("keydown", e => {
  if (!document.getElementById("pda-modal").classList.contains("hidden")) {
    if (e.key === "Escape") closePda();
    return;
  }
  const k = e.key.toLowerCase();
  if (k === "w") player.y = Math.max(20, player.y - player.speed);
  if (k === "s") player.y = Math.min(canvas.height - 20, player.y + player.speed);
  if (k === "a") player.x = Math.max(20, player.x - player.speed);
  if (k === "d") player.x = Math.min(canvas.width - 20, player.x + player.speed);
  if (k === "e") interact();
  if (k === "tab") { e.preventDefault(); openPda(); }
  const near = getNearObject();
  document.getElementById("interact-hint").textContent = near ? `按 E 與「${near.label}」互動` : "靠近物件按 E 互動";
  drawMap();
});

const pdaModal = document.getElementById("pda-modal");
async function openPda() {
  pdaModal.classList.remove("hidden");
  document.getElementById("term-input").focus();
  const res = await fetch("/api/config");
  const data = await res.json();
  document.getElementById("cfg-editor").value = data.content || "";
}
function closePda() { pdaModal.classList.add("hidden"); }

document.getElementById("btn-pda").onclick = openPda;
document.getElementById("btn-close-pda").onclick = closePda;

document.querySelectorAll(".tab").forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll(".tab, .tab-content").forEach(el => el.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
  };
});

function appendTerm(text) {
  const out = document.getElementById("term-output");
  out.textContent += text + "\n";
  out.scrollTop = out.scrollHeight;
}

function renderState(state) {
  latestState = state;
  document.getElementById("term-prompt").textContent = `employee@office:${state.cwd}$`;
  let doneCount = 0;
  Object.entries(state.tasks).forEach(([k, v]) => {
    const li = document.querySelector(`li[data-task="${k}"]`);
    if (li) li.classList.toggle("done", v);
    if (v) doneCount++;
  });
  document.getElementById("progress-text").textContent = `任務完成度：${doneCount} / 10`;
  document.getElementById("token-s1").textContent = state.tokens.stage1 || "尚未解鎖";
  document.getElementById("token-s2").textContent = state.tokens.stage2 || "尚未解鎖";
  document.getElementById("token-s3").textContent = state.tokens.stage3 || "尚未解鎖";

  const s3Box = document.getElementById("stage3-box");
  if (state.stage3_unlocked) {
    s3Box.classList.remove("locked");
    document.getElementById("stage-badge").textContent = "階段三：定期員工考核";
    document.getElementById("stage3-desc").textContent =
      "主管已出現在辦公室右上角！請排查日誌、終止異常進程、修復 config.conf PORT=8080 並將機密檔設為 600。";
  }
  drawMap();
}

document.getElementById("term-form").onsubmit = async e => {
  e.preventDefault();
  const input = document.getElementById("term-input");
  const cmd = input.value;
  input.value = "";
  appendTerm(`${document.getElementById("term-prompt").textContent} ${cmd}`);
  const res = await fetch("/api/exec", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cmd })
  });
  const data = await res.json();
  if (data.output) appendTerm(data.output);
  renderState(data.state);
};

document.getElementById("btn-save-cfg").onclick = async () => {
  const content = document.getElementById("cfg-editor").value;
  const res = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content })
  });
  const data = await res.json();
  renderState(data.state);
  alert("設定檔已儲存！");
};

document.getElementById("btn-reset").onclick = async () => {
  const res = await fetch("/api/reset", { method: "POST" });
  const data = await res.json();
  document.getElementById("term-output").textContent = "";
  renderState(data.state);
};

(async () => {
  appendTerm("Metis Office OS v1.0 - 輸入 help 查看可用指令");
  const res = await fetch("/api/state");
  renderState(await res.json());
})();
