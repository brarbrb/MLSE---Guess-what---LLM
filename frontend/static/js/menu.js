(function(){
  const $ = (sel) => document.querySelector(sel);

  const overlay     = $("#overlay");
  const panelNew    = $("#panel-new");
  const panelJoin   = $("#panel-join");
  const panelLobby  = $("#panel-lobby");

  const btnNew      = $("#btn-new");
  const btnJoin     = $("#btn-join");
  const btnStart    = $("#btn-start");
  const formNew     = $("#form-new");
  const formJoin    = $("#form-join-code");
  const btnJoinRnd  = $("#btn-join-random");

  let currentGame = null;     // { id, code, isCreator }
  let lobbyTimer = null;

  function openPanel(panel){
    overlay.hidden = false;
    panel.hidden = false;
  }
  function closePanels(){
    overlay.hidden = true;
    [panelNew, panelJoin, panelLobby].forEach(p=> p.hidden = true);
    if (lobbyTimer){ clearInterval(lobbyTimer); lobbyTimer = null; }
  }
  document.addEventListener("click", (e) => {
    if (e.target.matches("[data-close]")) closePanels();
  });

  // --- New game flow ---
  btnNew?.addEventListener("click", () => openPanel(panelNew));

  formNew?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(formNew);
    const payload = {
      round_time:  Number(fd.get("round_time")),
      difficulty:  String(fd.get("difficulty")),
      allow_hints: fd.get("allow_hints") === "on",
      max_hints:   Number(fd.get("max_hints")),
      max_players: Number(fd.get("max_players")),
      is_private:  fd.get("is_private") === "on",
      total_rounds:Number(fd.get("total_rounds")),
    };
    const res = await fetch("/api/games", {
      method: "POST",
      headers: { "Content-Type":"application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.ok){ alert(data.error || "Failed to create"); return; }

    currentGame = { id: data.game_id, code: data.game_code, isCreator:true };
    // switch to lobby panel
    panelNew.hidden = true;
    renderLobbyHeader();
    openPanel(panelLobby);
    startLobbyPolling();
    btnStart.hidden = false; // creator can start
  });

  // --- Join flow ---
  btnJoin?.addEventListener("click", () => openPanel(panelJoin));

  formJoin?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(formJoin);
    const code = String(fd.get("game_code") || "").toUpperCase().trim();
    if (!code) return;

    const res = await fetch("/api/games/join_by_code", {
      method: "POST",
      headers: { "Content-Type":"application/json" },
      body: JSON.stringify({ game_code: code })
    });
    const data = await res.json();
    if (!res.ok || !data.ok){ alert(data.error || "Join failed"); return; }

    currentGame = { id: data.game_id, code: data.game_code, isCreator:false };
    panelJoin.hidden = true;
    renderLobbyHeader();
    openPanel(panelLobby);
    btnStart.hidden = true; // only creator
    startLobbyPolling();
  });

  btnJoinRnd?.addEventListener("click", async () => {
    const res = await fetch("/api/games/join_random", { method: "POST" });
    const data = await res.json();
    if (!res.ok || !data.ok){ alert(data.error || "No games available"); return; }
    currentGame = { id: data.game_id, code: data.game_code, isCreator:false };
    panelJoin.hidden = true;
    renderLobbyHeader();
    openPanel(panelLobby);
    btnStart.hidden = true;
    startLobbyPolling();
  });

  // --- Lobby polling ---
  async function pollLobby(){
    if (!currentGame) return;
    const res = await fetch(`/api/games/${currentGame.id}/lobby`);
    const data = await res.json();
    if (!res.ok || !data.ok){ return; }

    // fill players
    const ul = $("#lobby-players");
    ul.innerHTML = "";
    data.players.forEach(name => {
      const li = document.createElement("li");
      li.textContent = name;
      ul.appendChild(li);
    });

    // update header
    const meta = $("#lobby-meta");
    meta.innerHTML = `
      <div>Status: <b>${data.status}</b></div>
      ${data.game_code ? `<div>Game code: <b>${data.game_code}</b></div>` : ""}
      <div>Players: ${data.players.length} / ${data.max_players}</div>
    `;

    // if game started elsewhere, you might redirect to game room here
    if (data.status === "active"){
      // e.g., window.location.href = `/room/${currentGame.id}`;
    }
  }

  function startLobbyPolling(){
    pollLobby();
    lobbyTimer = setInterval(pollLobby, 2000);
  }

  function renderLobbyHeader(){
    $("#lobby-meta").textContent = "Loading...";
    $("#lobby-players").innerHTML = "";
    openPanel(panelLobby);
  }

  // --- Start game (creator only) ---
  btnStart?.addEventListener("click", async () => {
    if (!currentGame?.isCreator) return;
    const res = await fetch(`/api/games/${currentGame.id}/start`, { method:"POST" });
    const data = await res.json();
    if (!res.ok || !data.ok){ alert(data.error || "Start failed"); return; }
    // go to actual game view (route TBD)
    // window.location.href = `/room/${currentGame.id}`;
  });

})();
