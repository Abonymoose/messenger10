from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import random
import uuid
from collections import defaultdict

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# IP to User ID mapping
ip_to_id = {}
# Store user states
users = {}
# Chat logs per user ID
chat_logs = defaultdict(list)
# Active sessions
active_users = set()

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def on_connect():
    ip = request.remote_addr
    if ip not in ip_to_id:
        ip_to_id[ip] = str(uuid.uuid4())[:8]
    user_id = ip_to_id[ip]
    users[user_id] = {
        "step": "start",
        "name": "",
        "round": 1,
        "survived": True
    }
    active_users.add(user_id)
    emit('init', {
        'id': user_id,
        'chat': chat_logs[user_id],
        'active': len(active_users)
    })

@socketio.on('disconnect')
def on_disconnect():
    ip = request.remote_addr
    user_id = ip_to_id.get(ip)
    if user_id in active_users:
        active_users.remove(user_id)
    socketio.emit('update_active', len(active_users), broadcast=True)

@socketio.on('chat')
def on_chat(data):
    ip = request.remote_addr
    user_id = ip_to_id[ip]
    msg = data['msg']
    chat_logs[user_id].append((user_id, msg))
    socketio.emit('chat', {'id': user_id, 'msg': msg})

@socketio.on('rr_message')
def on_rr(msg):
    ip = request.remote_addr
    user_id = ip_to_id[ip]
    user = users[user_id]
    response = process_rr(msg.strip(), user)
    socketio.emit('rr_response', {'id': user_id, 'msg': response})

def process_rr(msg, user):
    if user["step"] == "start":
        user["step"] = "get_name"
        return "??? : 'You... What is your name?'"

    elif user["step"] == "get_name":
        user["name"] = msg
        user["step"] = "intro"
        return f"??? : 'Ahh... {msg}... Yes, I remember now.'\nYou were once a legend of Russian Roulette...\nDo you want to play? (Y/N)"

    elif user["step"] == "intro":
        if msg.lower() == 'y':
            user["step"] = "round"
            user["round"] = 1
            return f"Round 1 begins...\nChance of survival: 80%\nType 'shoot' to pull the trigger."
        elif msg.lower() == 'n':
            user["step"] = "exit"
            return "You chose not to play. You walk away into the night... THE END."
        else:
            return "Please type 'Y' to play or 'N' to refuse."

    elif user["step"] == "round":
        if msg.lower() == "shoot":
            round_num = user["round"]
            chance = 1 - (round_num * 0.2)
            if random.random() > chance:
                user["step"] = "dead"
                return f"You pulled the trigger... BANG! You died in Round {round_num}."
            else:
                user["round"] += 1
                if user["round"] > 4:
                    user["step"] = "won"
                    return f"You survived all 4 rounds!\nKevin: 'So, will you join me?' (Y/N)"
                else:
                    return f"CLICK! You survived Round {round_num}.\nPrepare for Round {user['round']} (Type 'shoot')."
        else:
            return "Type 'shoot' to pull the trigger."

    elif user["step"] == "won":
        if msg.lower() == 'y':
            user["step"] = "end"
            return "Kevin smiles.\nYou have joined the underground.\nTo be continued in Russian Roulette 2..."
        elif msg.lower() == 'n':
            user["step"] = "robber"
            return "You walk away...\nA robber attacks you in the street...\nYou try to fight but you're stabbed.\nDarkness closes in...\nTHE END."
        else:
            return "Please respond with 'Y' or 'N'."

    elif user["step"] in ["dead", "exit", "robber", "end"]:
        return "GAME OVER. Refresh the page to play again."

    return "Unrecognized input. Try again."

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=81)
