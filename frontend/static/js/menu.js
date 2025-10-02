// frontend/static/js/menu.js
(function () {
  // Wait for DOM (in case script isn't loaded with `defer`)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  function init() {
    const $  = (sel, root = document) => root.querySelector(sel);

    // Panels/overlay
    const overlay    = $("#overlay");
    const panelNew   = $("#panel-new");
    const panelJoin  = $("#panel-join");
    const panelLobby = $("#panel-lobby");

    // Buttons/forms
    const btnNew     = $("#btn-new");
    const btnJoin    = $("#btn-join");
    const btnStart   = $("#btn-start");
    const formNew    = $("#form-new");
    const formJoin   = $("#form-join-code");
    const btnJoinRnd = $("#btn-join-random");

    // Inputs inside "Create game" form
    const allowHints = formNew?.querySelector("input[name='allow_hints']");
    const maxHints   = formNew?.querySelector("input[name='max_hints']");

    // State
    let currentGame = null;   // { id, code, isCreator }
    let lobbyTimer  = null;

    // ---------- UI helpers ----------
    function openPanel(panel){
      if (!panel) return;
      overlay.hidden = false;
      panel.hidden = false;
      document.body.classList.add("modal-open");
    }

    function closePanels(){
      overlay.hidden = true;
      [panelNew, panelJoin, panelLobby].forEach(p => { if (p) p.hidden = true; });
      document.body.classList.remove("modal-open");
      if (lobbyTimer){ clearInterval(lobbyTimer); lobbyTimer = null; }
    }

    // Close handler for any element with [data-close]
    document.addEventListener("click", (e) => {
      if (e.target.matches("[data-close]")) closePanels();
    });

    // ---------- Create game flow ----------
    btnNew?.addEventListener("click", () => openPanel(panelNew));

    // Toggle "Max hints" enable/disable based on "Allow hints"
    function syncHintsState() {
      if (!allowHints || !maxHints) return;
      if (allowHints.checked) {
        maxHints.disabled = false;
        if (maxHints.value === "0") maxHints.value = "3"; // restore a sensible default
      } else {
        maxHints.disabled = true;
        maxHints.value = "0";
      }
    }
    allowHints?.addEventListener("change", syncHintsState);
    syncHintsState(); // set initial state on load

    formNew?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(formNew);
      const payload = {
        round_time:   Number(fd.get("round_time")),
        difficulty:   String(fd.get("difficulty")),
        allow_hints:  fd.get("allow_hints") === "on",
        max_hints:    Number(fd.get("max_hints")),
        max_players:  Number(fd.get("max_players")),
        is_private:   fd.get("is_private") === "on",
        total_rounds: Number(fd.get("total_rounds")),
      };

      const res  = await fetch("/api/games", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) { alert(data.error || "Failed to create"); return; }

      currentGame = { id: data.game_id, code: data.game_code, isCreator: true };

      // Switch to lobby
      panelNew.hidden = true;
      renderLobbyHeader();
      openPanel(panelLobby);
      btnStart && (btnStart.hidden = false);    // creator can start
      startLobbyPolling();
    });

    // ---------- Join flow ----------
    btnJoin?.addEventListener("click", () => openPanel(panelJoin));

    formJoin?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd   = new FormData(formJoin);
      const code = String(fd.get("game_code") || "").toUpperCase().trim();
      if (!code) return;

      const res  = await fetch("/api/games/join_by_code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_code: code }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) { alert(data.error || "Join failed"); return; }

      currentGame = { id: data.game_id, code: data.game_code, isCreator: false };

      panelJoin.hidden = true;
      renderLobbyHeader();
      openPanel(panelLobby);
      btnStart && (btnStart.hidden = true);     // only creator can start
      startLobbyPolling();
    });

    btnJoinRnd?.addEventListener("click", async () => {
      const res  = await fetch("/api/games/join_random", { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) { alert(data.error || "No games available"); return; }

      currentGame = { id: data.game_id, code: data.game_code, isCreator: false };

      panelJoin.hidden = true;
      renderLobbyHeader();
      openPanel(panelLobby);
      btnStart && (btnStart.hidden = true);
      startLobbyPolling();
    });

    // ---------- Lobby ----------
    async function pollLobby() {
      if (!currentGame) return;

      const res  = await fetch(`/api/games/${currentGame.id}/lobby`);
      const data = await res.json();
      if (!res.ok || !data.ok) return;

      // Players
      const ul = $("#lobby-players");
      if (ul) {
        ul.innerHTML = "";
        data.players.forEach(name => {
          const li = document.createElement("li");
          li.textContent = name;
          ul.appendChild(li);
        });
      }

      // Meta
      const meta = $("#lobby-meta");
      if (meta) {
        meta.innerHTML = `
          <div>Status: <b>${data.status}</b></div>
          ${data.game_code ? `<div>Game code: <b>${data.game_code}</b></div>` : ""}
          <div>Players: ${data.players.length} / ${data.max_players}</div>
        `;
      }

      // If game started elsewhere, redirect (hook up your game room route here)
      if (data.status === "active") {
        // window.location.href = `/room/${currentGame.id}`;
      }
    }

    function startLobbyPolling() {
      pollLobby();
      lobbyTimer = setInterval(pollLobby, 2000);
    }

    function renderLobbyHeader() {
      const meta = $("#lobby-meta");
      const ul   = $("#lobby-players");
      if (meta) meta.textContent = "Loading...";
      if (ul)   ul.innerHTML = "";
      openPanel(panelLobby);
    }

    // ---------- Start (creator only) ----------
    btnStart?.addEventListener("click", async () => {
      if (!currentGame?.isCreator) return;

      const res  = await fetch(`/api/games/${currentGame.id}/start`, { method: "POST" });
      const data = await res.json();
      if (!res.ok || !data.ok) { alert(data.error || "Start failed"); return; }

      // window.location.href = `/room/${currentGame.id}`;
    });
  }
})();
