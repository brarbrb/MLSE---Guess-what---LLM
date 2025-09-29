function createRoom() {
    fetch("/api/room/new", {
        method: "POST",
        body: JSON.stringify({username: currentUser.username}),
        headers: {"Content-Type": "application/json"},
    }).then(response => response.json()).then((data) => {
        if (data.success) {
            window.location.href = `/room/${data.roomId}`;
        } else {
            throw new Error(data.message);
        }
    }).catch(error => {
        alert(error)
    });
}


function joinRandomRoom() {
    fetch("/api/room/join", {
        method: "POST",
        body: JSON.stringify({username: currentUser.username}),
        headers: {"Content-Type": "application/json"},
    }).then(response => response.json()).then((data) => {
        if (data.success) {
            window.location.href = `/room/${data.roomId}`;
        } else {
            throw new Error(data.message);
        }
    }).catch(error => {
        alert(error)
    });
}
