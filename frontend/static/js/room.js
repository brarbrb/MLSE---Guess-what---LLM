(function () {
  const $  = (s, r=document)=>r.querySelector(s);
  const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));

  const state = {
    gameId: null,
    roundNo: null,        
    reviewMode: false,    
    user: {},
    startedAt: null,
    timerId: null,
    isCreator: false,
    betweenRounds: false
  };

  const overlay = $("#modal-overlay");
  const modals = {
    describer: $("#modal-describer"),
    waiting:   $("#modal-waiting"),
    winner:    $("#modal-winner"),
  };

    const dsec = {
    loading:   $("#describer-loading"),
    ready:     $("#describer-ready"),
    verifying: $("#describer-verifying"),
    target:    $("#modal-target"),
    forb:      $("#modal-forbidden"),
    form:      $("#describer-form"),
    descInput: $("#description-input"),
    descErr:   $("#desc-error")
  };

  // --------- URL helpers ---------
  function parsePath() {
    // Supports /room/<id> and /room/<id>/<round>
    const m = location.pathname.match(/^\/room\/(\d+)(?:\/(\d+))?/);
    return {
      gameId: m ? Number(m[1]) : null,
      roundNo: m && m[2] ? Number(m[2]) : null
    };
  }
  function getQueryParam(name) {
    return new URLSearchParams(location.search).get(name);
  }

  function nowUtcISO() { return new Date().toISOString(); }

  function showModal(m) { overlay.hidden = false; m.hidden = false; }
  function hideModal(m) { m.hidden = true; if (![...Object.values(modals)].some(x=>!x.hidden)) overlay.hidden = true; }

  function setBadge(text){ $("#round-status").textContent = text; }
  function setDesc(text){ $("#round-description").textContent = text || "—"; }
  function renderPlayers(list,scores={}) {
    const ul = $("#players-list"); ul.innerHTML="";
    (list||[]).forEach(n=>{
      const li=document.createElement("li");
      li.textContent = `${n}: ${scores[n]??0} points`;
      ul.appendChild(li);
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

  function topThree(scoresObj = {}) {
    const arr = Object.entries(scoresObj).map(([name, score]) => ({ name, score: Number(score||0) }));
    arr.sort((a,b)=> b.score - a.score);
    return arr.slice(0,3);
  }

  // ---------- REST ----------
  async function getRoom() {
    // In review mode or when URL has explicit round -> use round-specific API
    if (state.reviewMode || state.roundNo) {
      const rn = state.roundNo || 1;
      const r = await fetch(`/api/room/${state.gameId}/round/${rn}`);
      return r.json();
    } else {
      const r = await fetch(`/api/room/${state.gameId}`);
      return r.json();
    }
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
      // ---------- CHAT HISTORY (on page load) ----------
    async function loadChatHistory({ round = 'current', limit = 200 } = {}) {
      const gid = state.gameId;
      if (!gid) return;

      const params = new URLSearchParams();
      if (round) params.set('round', round);   // 'current' or unset for all
      if (limit) params.set('limit', String(limit));

      try {
        const res  = await fetch(`/api/room/${gid}/chat?` + params.toString(), { credentials: 'same-origin' });
        const data = await res.json();
        if (!res.ok || !data.ok) return;

        // clear + render
        const box = $("#chat-list");
        if (box) box.innerHTML = '';
        (data.messages || []).forEach(m => addChatLine(m.user, m.text, m.ts, m.type));
      } catch (e) {
        console.error('chat history load failed', e);
      }
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
        socket.on("connect", ()=>{
      socket.emit("room:join", { game_id: state.gameId });
      // optimistic loader for creators until first snapshot arrives
      if (!state.reviewMode && state.isCreator) {
        dsec.loading && (dsec.loading.hidden = false);
        dsec.ready && (dsec.ready.hidden = true);
        dsec.verifying && (dsec.verifying.hidden = true);
        showModal(modals.describer);
      }
    });

    socket.on("chat:new", (msg)=> addChatLine(msg.user, msg.text));
    socket.on("round:description", (data)=> onDescriptionLive(data));
    socket.on("round:won", (data)=> onWinnerLive(data));
  }

  // ---------- SNAPSHOT -> UI ----------
  function applySnapshot(d, {from}={}){
    // creator lock
    state.isCreator = (d.turn && (d.turn === (state.user?.username||"")));
    const inp = $("#chat-input");
    const btn = $("#chat-send");
    const isCompleted = (d.status === 'completed');

    if (inp) inp.disabled = !!state.isCreator || state.reviewMode|| isCompleted;
    if (btn) btn.disabled = !!state.isCreator || state.reviewMode|| isCompleted;

    // Optional: note when blocked
    let note = document.getElementById("creator-chat-note");
    if (state.isCreator && !state.reviewMode) {
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
    window.__lastScores = d.scores || {};

    // round title text: "Round N"
    const rt = document.getElementById('round-title');
    if (rt) rt.textContent = `Round ${Number(d.roundNumber || state.roundNo || 1)}`;

    // expose total rounds for review nav
    const main = document.querySelector('main') || document.body;
    main.setAttribute('data-total-rounds', String(d.totalRounds || 0));

    // status & description
    setBadge(d.status || "waiting");
    if (d.description) setDesc(d.description);

    // timers
    if (!state.reviewMode && d.status === "active" && d.startedAt) startTimer(d.startedAt);
    if (d.status !== "active") startTimer(null);

    // modals (no modals in review mode)
    // modals (no modals in review mode)
    if (!state.reviewMode) {
      if (state.betweenRounds) {
        hideModal(modals.describer);
        hideModal(modals.waiting);
      } else if (d.status === "waiting_description") {
        if (state.isCreator) {
          // CREATOR: show loading until target/forbidden arrive, then show ready
          if (d.targetWord && (d.forbiddenWords || []).length) {
            // fill data + show READY
            dsec.target && (dsec.target.textContent = d.targetWord || "—");
            if (dsec.forb) {
              dsec.forb.innerHTML = "";
              (d.forbiddenWords || []).forEach(w => {
                const li = document.createElement("li");
                li.textContent = w;
                dsec.forb.appendChild(li);
              });
            }
            dsec.loading && (dsec.loading.hidden = true);
            dsec.verifying && (dsec.verifying.hidden = true);
            dsec.ready && (dsec.ready.hidden = false);
          } else {
            // still generating → LOADING
            dsec.loading && (dsec.loading.hidden = false);
            dsec.ready && (dsec.ready.hidden = true);
            dsec.verifying && (dsec.verifying.hidden = true);
          }
          showModal(modals.describer);
        } else {
          // PLAYERS: waiting with spinner
          $("#waiting-title").textContent = "Waiting for description…";
          $("#waiting-text").textContent  = "The describer is preparing a clue.";
          showModal(modals.waiting);
        }
      } else if (d.status === "active") {
        // when round actually starts, close all prep modals
        hideModal(modals.describer);
        hideModal(modals.waiting);
      } else if (d.status === "completed") {
        startTimer(null);
      }
    }


  }

  // live handlers
  function onDescriptionLive(data){
    if (state.reviewMode || state.betweenRounds) return;

    // everyone gets the description text
    const desc = data.description || "";
    setDesc(desc);
    setBadge("active");
    startTimer(data.startedAt || null);

    // players: drop the waiting modal
    hideModal(modals.waiting);

    // describer: close the modal if it was verifying/loading
    hideModal(modals.describer);

    // small flair for players that were waiting
    $("#waiting-title").textContent = "Description ready!";
    $("#waiting-text").textContent  = desc;
    $("#modal-waiting").classList.add("fade-in");
    setTimeout(()=> hideModal(modals.waiting), 1200);
  }


function onWinnerLive(data){
  if (state.reviewMode) return;

  // stop & mark completed for this round
  startTimer(null);
  setBadge("completed");
  hideModal(modals.describer);
  hideModal(modals.waiting);

  const roundNumber = Number(data?.roundNumber || 1);
  const totalRounds = Number(data?.totalRounds || 1);
  const isLast = !!data?.gameCompleted || (roundNumber >= totalRounds);

  $("#winner-name").textContent = data?.winner || "Someone";
  $("#winner-word").textContent = data?.word || "";
  $("#winner-time").textContent = (typeof data?.elapsedMs === "number")
    ? `Time: ${(data.elapsedMs/1000).toFixed(1)}s` : "";

  const actionsSel = "#modal-winner .actions, #modal-winner .panel-actions, #modal-winner .modal-actions";

  if (!isLast) {
    // === BETWEEN ROUNDS (not last) ===
    state.betweenRounds = true;                 // block any other modals during countdown

    // Close other modals just in case
    hideModal(modals.describer);
    hideModal(modals.waiting);

    // Robustly hide actions & both buttons
    const winner = document.getElementById("modal-winner");
    const actions = winner?.querySelector(".modal-actions");
    if (actions) {
      actions.hidden = true;
      actions.style.display = "none";
    }
    const seeGameBtn = document.getElementById("btn-see-game");
    if (seeGameBtn) { seeGameBtn.hidden = true; seeGameBtn.style.display = "none"; }
    const exitBtn = winner?.querySelector(".btn.danger");
    if (exitBtn) { exitBtn.hidden = true; exitBtn.style.display = "none"; }

    // Countdown text
    const countdownEl = document.getElementById("between-rounds-countdown");
    if (countdownEl) {
      countdownEl.hidden = false;
      let remain = 10;
      countdownEl.textContent = `The next round will start in ${remain}s`;
      const timer = setInterval(()=>{
        remain -= 1;
        if (remain <= 0) {
          clearInterval(timer);
          const next = roundNumber + 1;
          window.location.href = `/room/${state.gameId}/${next}`;
        } else {
          countdownEl.textContent = `The next round will start in ${remain}s`;
        }
      }, 1000);
    }

    showModal(modals.winner);
    return;
  } else {
    // === LAST ROUND ===
    const podium = topThree(window.__lastScores || {});
    const box = document.getElementById("winner-final-results");
    if (box) {
      box.innerHTML = podium.length
        ? `<ol>${podium.map(p=>`<li><b>${p.name}</b> — ${p.score} pts</li>`).join("")}</ol>`
        : `<p class="muted">No scores.</p>`;
      box.hidden = false;
    }
    const actions = document.querySelector(actionsSel);
    if (actions) actions.hidden = false;

    showModal(modals.winner);
  }
}



  // ---------- Review navigation ----------
  function setupReviewNav(){
    const nav = document.getElementById("review-nav");
    if (!nav) return;
    nav.hidden = false;

    const prev = document.getElementById("review-prev");
    const next = document.getElementById("review-next");

    const rn = state.roundNo || 1;
    const total = Number((document.querySelector('main')||document.body).getAttribute('data-total-rounds')) || rn;

    prev?.addEventListener('click', ()=>{
      const target = Math.max(1, (state.roundNo || 1) - 1);
      window.location.href = `/room/${state.gameId}/${target}?review=1`;
    });
    next?.addEventListener('click', ()=>{
      const target = Math.min(total, (state.roundNo || 1) + 1);
      window.location.href = `/room/${state.gameId}/${target}?review=1`;
    });
  }

  // ---------- FORMS ----------
  function setupForms(){
    // describer submit
    $("#describer-form")?.addEventListener("submit", async (e)=>{
      e.preventDefault();
      const txt=$("#description-input").value.trim();
      if(!txt) return;
      const res = await sendDescription(txt);

      if (res?.error) {
        if (dsec.descErr) {
          dsec.descErr.textContent = res.which
            ? `Description invalid: contains "${res.which}".`
            : (res.error || "Failed to submit.");
          dsec.descErr.hidden = false;
        }
        // stay on READY so user can edit and resubmit
        dsec.loading && (dsec.loading.hidden = true);
        dsec.ready && (dsec.ready.hidden = false);
        dsec.verifying && (dsec.verifying.hidden = true);
        return;
      }

      // switch to VERIFYING (do NOT close modal yet)
      if (dsec.descErr) dsec.descErr.hidden = true;
      dsec.loading && (dsec.loading.hidden = true);
      dsec.ready && (dsec.ready.hidden = true);
      dsec.verifying && (dsec.verifying.hidden = false);
      // wait for server to confirm (either snapshot d.status === "active" or socket "round:description")

    });

    // LAST-round-only button (we show it only on last round)
    $("#btn-see-game")?.addEventListener("click", ()=>{
      // enter review mode at round 1
      window.location.href = `/room/${state.gameId}/1?review=1`;
    });
    // Always prevent form submission (avoids page reload in review mode)
    $("#chat-form")?.addEventListener("submit", async (e)=>{
      e.preventDefault();

      // Block sending when creator, in review mode, or if game completed (handled in applySnapshot too)
      if (state.isCreator || state.reviewMode) return;

      const input = $("#chat-input");
      const text  = input?.value.trim();
      if (!text) return;

      await sendGuess(text);           // backend handles scoring & emits chat/new + round:won if needed
      if (input) input.value = "";
    });

  }

  // ---------- init ----------
  (function init(){
    const p = parsePath();
    state.gameId = p.gameId;
    state.roundNo = p.roundNo || null;
    state.reviewMode = getQueryParam('review') === '1';
    if (state.reviewMode) {
      const inp = $("#chat-input");
      const btn = $("#chat-send");
      if (inp) inp.disabled = true;
      if (btn) btn.disabled = true;
    }

    try { state.user = JSON.parse(localStorage.getItem("currentUser")||"{}"); } catch {}

    if(!state.gameId) return;

    setupForms();

    if (state.reviewMode) {
      // No sockets/polling in review mode—load once & show nav
      (async ()=>{
        const data = await getRoom();
        if (!data.error) applySnapshot(data, { from: "review" });
        // show chat history for *this round* in review mode
        await loadChatHistory({ round: 'current' });
        setupReviewNav();
      })();
    } else {
      setupSockets();
      startPolling();
      // show chat history for the *current* live round
      loadChatHistory({ round: 'current' });
    }
  })();
})();
