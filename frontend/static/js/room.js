(function () {
  const $  = (s, r=document)=>r.querySelector(s);
  const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));

  const state = {
    gameId: null,
    user: {},
    startedAt: null,
    timerId: null,
    isCreator: false
  };

  const overlay = $("#modal-overlay");
  const modals = {
    describer: $("#modal-describer"),
    waiting: $("#modal-waiting"),
    winner: $("#modal-winner"),
  };

  function getGameId() {
    const m = location.pathname.match(/\/room\/(\d+)/);
    return m ? Number(m[1]) : null;
  }

  function nowUtcISO() { return new Date().toISOString(); }

  function showModal(m) { overlay.hidden = false; m.hidden = false; }
  function hideModal(m) { m.hidden = true; if (![...Object.values(modals)].some(x=>!x.hidden)) overlay.hidden = true; }

  function setBadge(text){ $("#round-status").textContent = text; }
  function setDesc(text){ $("#round-description").textContent = text || "—"; }
  function renderPlayers(list,scores={}) {
    const ul = $("#players-list"); ul.innerHTML="";
    (list||[]).forEach(n=>{
      const li=document.createElement("li"); li.textContent = `${n}: ${scores[n]??0} points`; ul.appendChild(li);
    });
  }

  function addChatLine(user,text){
    const box=$("#chat-list");
    const div=document.createElement("div");
    div.className="chat-item";
    div.innerHTML = `<span class="u">${user}</span><span>${text}</span>`;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
  }

  function startTimer(iso) {
    const el=$("#round-timer");
    if (state.timerId) { clearInterval(state.timerId); state.timerId=null; }
    if (!iso){ el.hidden=true; return; }
    const start = new Date(iso).getTime();
    el.hidden=false;
    state.timerId = setInterval(()=>{
      const d = Date.now()-start;
      const m = Math.floor(d/60000).toString().padStart(2,"0");
      const s = Math.floor((d%60000)/1000).toString().padStart(2,"0");
      el.textContent = `${m}:${s}`;
    }, 250);
  }

  // ---------- REST ----------
  async function getRoom() {
    const r = await fetch(`/api/room/${state.gameId}`); return r.json();
  }
  async function sendDescription(text) {
    const r = await fetch(`/api/room/${state.gameId}/description`, {
      method:"PUT", headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ description: text })
    });
    return r.json();
  }
  async function sendGuess(text) {
    const r = await fetch(`/api/room/${state.gameId}/guess`, {
      method:"PUT", headers:{ "Content-Type":"application/json" },
      body: JSON.stringify({ guess: text })
    });
    return r.json();
  }

  // ---------- POLLING ----------
  let pollId=null;
  function startPolling(){
    stopPolling();
    const tick = async ()=>{
      try {
        const data = await getRoom();
        if (data.error) return;
        applySnapshot(data, { from: "poll" });
      } catch { /* ignore */ }
    };
    tick();
    pollId = setInterval(tick, 1500);
  }
  function stopPolling(){ if(pollId) clearInterval(pollId); pollId=null; }

  // ---------- SOCKETS ----------
  function setupSockets(){
    if (typeof io === "undefined") return;
    const socket = io();
    socket.on("connect", ()=> socket.emit("room:join", { game_id: state.gameId }));
    socket.on("chat:new", (msg)=> addChatLine(msg.user, msg.text));
    socket.on("round:description", (data)=> onDescriptionLive(data));
    socket.on("round:won", (data)=> onWinnerLive(data));
    // send chat guesses through socket too (optional)
    $("#chat-form")?.addEventListener("submit", (e)=>{
      e.preventDefault();
      if (state.isCreator) return;
      const t = $("#chat-input").value.trim();
      if (!t) return;
      // addChatLine(state.user?.username || "me", t); // keep commented if server echoes back
      socket.emit("chat:send", { game_id: state.gameId, text: t });
      $("#chat-input").value = ""; // clear input
    });
  }

  // ---------- SNAPSHOT -> UI ----------
  function applySnapshot(d, {from}={}){
    // who is creator
    state.isCreator = (d.turn && (d.turn === (state.user?.username||"")));
    const inp = $("#chat-input");
    const btn = $("#chat-send");
    if (inp) inp.disabled = !!state.isCreator;
    if (btn) btn.disabled = !!state.isCreator;

    // Optional: small note at the top of the chat when blocked
    let note = document.getElementById("creator-chat-note");
    if (state.isCreator) {
      if (!note) {
        note = document.createElement("div");
        note.id = "creator-chat-note";
        note.className = "muted";
        note.style.marginBottom = "6px";
        note.textContent = "Creators can't chat while describing.";
        const chat = $("#chat-list")?.parentElement || $("#chat");
        if (chat) chat.insertBefore(note, chat.firstChild);
      }
    } else if (note) {
      note.remove();
    }
    // players & scores
    renderPlayers(d.players || [], d.scores || {});
    // status
    setBadge(d.status || "waiting");
    // description (if active)
    if (d.description) setDesc(d.description);

    // timers
    if (d.status === "active" && d.startedAt) startTimer(d.startedAt);
    if (d.status !== "active") startTimer(null);

    // modals
    if (d.status === "waiting_description") {
      if (state.isCreator) {
        // creator sees describer modal
        $("#modal-target").textContent = d.targetWord || "—";
        const ul=$("#modal-forbidden"); ul.innerHTML="";
        (d.forbiddenWords||[]).forEach(w=>{ const li=document.createElement("li"); li.textContent=w; ul.appendChild(li); });
        showModal(modals.describer);
      } else {
        // players see waiting modal
        $("#waiting-title").textContent = "Waiting for description…";
        $("#waiting-text").textContent = "The describer is preparing a clue.";
        showModal(modals.waiting);
      }
    } else if (d.status === "active") {
      // ensure waiting closed
      hideModal(modals.describer);
      hideModal(modals.waiting);
    } else if (d.status === "completed") {
      // handled by winner popup usually; make sure timer stops
      startTimer(null);
    }
  }

  // live handlers
  function onDescriptionLive(data){
    // change waiting modal text and close after 3s with a small fade
    $("#waiting-title").textContent = "Description ready!";
    $("#waiting-text").textContent  = data.description || "";
    $("#modal-waiting").classList.add("fade-in");
    startTimer(data.startedAt || null);
    setDesc(data.description || "");
    setBadge("active");
    setTimeout(()=> hideModal(modals.waiting), 3000);
  }

function onWinnerLive(data){
  // stop & hide the running round timer
  startTimer(null);

  // mark the round as completed in the UI
  setBadge("completed");

  $("#winner-name").textContent = data?.winner || "Someone";
  $("#winner-word").textContent = data?.word || "";
  $("#winner-time").textContent = (typeof data?.elapsedMs === "number")
    ? `Time: ${(data.elapsedMs/1000).toFixed(1)}s` : "";

  // make sure any other modals are closed
  hideModal(modals.describer);
  hideModal(modals.waiting);

  showModal(modals.winner);
}

  // ---------- FORMS ----------
  function setupForms(){
    // describer submit
    $("#describer-form")?.addEventListener("submit", async (e)=>{
      e.preventDefault();
      const txt=$("#description-input").value.trim();
      if(!txt) return;
      const res = await sendDescription(txt);
      if(res.error){
        const p=$("#desc-error"); p.textContent = res.which
          ? `Description invalid: contains "${res.which}".`
          : (res.error || "Failed to submit.");
        p.hidden = false;
        return;
      }
      $("#desc-error").hidden = true;
      hideModal(modals.describer);
      setDesc(txt);
      setBadge("active");
      // players will also get socket event if wired
    });
    $("#btn-see-game")?.addEventListener("click", ()=> hideModal(modals.winner));
  }

  // ---------- init ----------
  (function init(){
    state.gameId = getGameId();
    try { state.user = JSON.parse(localStorage.getItem("currentUser")||"{}"); } catch {}
    if(!state.gameId) return;

    setupForms();
    setupSockets();
    startPolling();
  })();
})();
