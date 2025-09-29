const currentUser = {username: null}


function loadUser() {
    const currentUserJSON = localStorage.getItem('currentUser');
    if (currentUserJSON) {
        updateUserData(JSON.parse(currentUserJSON));
    }
}


function login() {
    const username = prompt("Enter your username:");
    const password = prompt("Enter your password:");
    fetch("/api/login", {
        method: "POST",
        body: JSON.stringify({username, password}),
        headers: {"Content-Type": "application/json"},
    }).then(response => response.json()).then((data) => {
        if (data.success) {
            updateUserData(data.user);
        } else {
            throw new Error(data.message);
        }
    }).catch(error => {
        alert(error)
    });
}

function logout() {
    updateUserData({username: null});
}

function updateUserData(userData) {
    const {username, displayname} = userData;
    Object.keys(currentUser).forEach(key => {
        delete currentUser[key];
    });
    Object.assign(currentUser, userData);
    localStorage.setItem('currentUser', JSON.stringify(currentUser));
    if (username) {
        document.getElementById("username").innerText = `Hello, ${displayname}!`;
        document.getElementById("login-button").innerText = "Logout";
        document.getElementById("login-button").onclick = logout;
    } else {
        document.getElementById("username").innerText = "";
        document.getElementById("login-button").innerText = "Login";
        document.getElementById("login-button").onclick = login;
    }
}


window.addEventListener('load', function () {
    loadUser();
});
