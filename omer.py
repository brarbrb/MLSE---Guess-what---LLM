
from flask import Blueprint, request, jsonify
from flask_cors import CORS

from language_modal.forbidden_words import get_forbidden_words, GUESSED_WORDS

omer_bp = Blueprint('omer', __name__)
CORS(omer_bp)


users = {
    "Guess": {"password": "What", "displayname": "Player 1"},
    "What": {"password": "Guess", "displayname": "Player 2"}
}

# In memory storage of game rooms
rooms = {}

# Login endpoint
@omer_bp.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = users.get(username)
    if user and user["password"] == password:
        return jsonify({
            "success": True,
            "user": {
                "username": username,
                "displayname": user["displayname"]
            }
        })
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

# Create a new room (id = 1 for demo)
@omer_bp.route("/api/room/new", methods=["POST"])
def create_room():
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"success": False, "message": "You must be signed in to preform this action"}), 401
    room_id = 1

    if room_id in rooms:
        return jsonify({"success": False, "message": "Room already exists"}), 400

    rooms[room_id] = {
        "player1": username,
        "player2": None,
        "scores": {username: 0},
        "word": GUESSED_WORDS[room_id],
        "description": "",
        "forbidden": get_forbidden_words(GUESSED_WORDS[room_id]),
        "guess": None,
        "id": room_id
    }

    return jsonify({"success": True, "message": "Room demo-room created", "roomId": room_id})

# Auto-join player 2 to the first available room
@omer_bp.route("/api/room/join", methods=["POST"])
def auto_join_room():
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"success": False, "message": "You must be signed in to preform this action"}), 401

    for room_id, room in rooms.items():
        if room["player2"] is None:
            room["player2"] = username
            room["scores"][username] = 0
            return jsonify({
                "success": True,
                "message": f"{username} joined room demo-room",
                "roomId": room_id
            })

    return jsonify({
        "success": False,
        "message": "No available rooms to join"
    }), 404


@omer_bp.route("/api/room/<int:room_id>/description", methods=["PUT"])
def validate_description(room_id):
    # room_id = 1 when entering the page
    data = request.get_json()
    username = data.get("username")
    description = data.get("description")

    room = rooms.get(room_id)
    if not room:
        return jsonify({"success": False, "message": "Room not found"}), 404

    correct_word = room["word"].lower()
    if correct_word in description.lower():
        return {"valid": False}
    forbidden = get_forbidden_words(correct_word)
    for word in forbidden:
        if word in description.lower():
            return {"valid": False}

    room["description"] = description
    return {"valid": True}


# Handle word guessing
@omer_bp.route("/api/room/<int:room_id>/guess", methods=["PUT"])
def handle_guess(room_id):
    data = request.get_json()
    username = data.get("username")
    guess = data.get("guess")

    room = rooms.get(room_id)
    if not room:
        return jsonify({"success": False, "message": "Room not found"}), 404

    if guess.lower() == room["word"].lower():
        room["guess"] = guess
        room["scores"][username] += 1
        return jsonify({
            "correct": True,
            "score": room["scores"][username],
            "message": "Correct guess"
        })

    return jsonify({
        "correct": False,
        "score": room["scores"].get(username, 0),
        "message": "Wrong guess"
    })

# Get current room status 
@omer_bp.route("/api/room/<int:room_id>", methods=["GET"])
def get_room_status(room_id):
    room = rooms.get(room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    return jsonify({
        "turn": room["player1"],
        "scores": room["scores"],
        "forbidden": room["forbidden"],
        "guess": room["guess"],
        "description": room["description"],
        "id": room_id
    })
