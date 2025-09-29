const currentRoom = {id: null};


function loadRoom() {
    const currentRoomJSON = localStorage.getItem('currentRoom');
    if (currentRoomJSON) {
        updateRoomData(JSON.parse(currentRoomJSON));
    }
}

function submitDescription(event) {
    event.preventDefault();
    event.stopPropagation();
    const description = document.getElementById('description-input').value.trim();
    fetch(`/api/room/${currentRoom.id}/description`, {
        method: "PUT",
        body: JSON.stringify({username: currentUser.username, description}),
        headers: {"Content-Type": "application/json"},
    }).then(response => response.json()).then((data) => {
        if (data.valid) {
            alert("Updated description successfully.");
        } else {
            alert("Your description is invalid.");
        }
    }).catch(error => {
        alert(error)
    });
    return false;
}


function submitGuess(event) {
    event.preventDefault();
    event.stopPropagation();
    const guess = document.getElementById('guess-input').value.trim();
    fetch(`/api/room/${currentRoom.id}/guess`, {
        method: "PUT",
        body: JSON.stringify({username: currentUser.username, guess}),
        headers: {"Content-Type": "application/json"},
    }).then(response => response.json()).then((data) => {
        if (data.correct) {
            alert(data.message);
        } else {
            alert(data.message);
        }
    }).catch(error => {
        alert(error)
    });
    return false;
}

function updateScores(scores) {
    const listElement = document.getElementById("players-list");
    listElement.textContent = '';
    Object.entries(scores).forEach(([playerName, score]) => {
        const childElement = document.createElement("li");
        const playerNameElement = document.createElement("span");
        playerNameElement.textContent = `${playerName}: `;
        childElement.appendChild(playerNameElement);
        const playerScoreElement = document.createElement("span");
        playerScoreElement.textContent = `${score} points`;
        childElement.appendChild(playerScoreElement);
        listElement.appendChild(childElement);
    })
}


function updateDescription(description) {
    const descriptionElement = document.getElementById("current-description");
    descriptionElement.textContent = description ? description : "";
}


function fetchRoomData(roomId) {
    fetch(`/api/room/${roomId}`, {
        method: "GET",
        headers: {"Content-Type": "application/json"},
    }).then(response => response.json()).then((data) => {
        if (data.id) {
            updateRoomData(data);
        } else {
            throw new Error(data.message);
        }
    }).catch(error => {
        alert(error)
    });
}

function updateRoomData(roomData) {
    Object.keys(currentRoom).forEach(key => {
        delete currentRoom[key];
    });
    Object.assign(currentRoom, roomData);
    updateScores(roomData.scores);
    updateDescription(roomData.description);
    if (roomData.turn === currentUser.username) {
        document.getElementById("guesser-section").style.visibility = "hidden";
        document.getElementById("describer-section").style.visibility = "visible";
    } else {
        document.getElementById("guesser-section").style.visibility = "visible";
        document.getElementById("describer-section").style.visibility = "hidden";
    }
}

function getRoomIdFromURL() {
    return /room\/([^/]+)\/*$/i.exec(window.location.pathname)[1]
}


window.addEventListener('load', function () {
  loadRoom();
  document.getElementById("describer-form").addEventListener('submit', submitDescription);
  document.getElementById("guesser-form").addEventListener('submit', submitGuess);
  const roomId = getRoomIdFromURL();
  fetchRoomData(roomId);
  setInterval(() => fetchRoomData(roomId), 1000);
});
