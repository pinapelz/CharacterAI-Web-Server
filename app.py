from flask import Flask, request, abort, jsonify
from database.sql_handler import SQLHandler
from flask_cors import CORS
import configparser
from cai import ChatSession
from gevent import monkey

monkey.patch_all()
app = Flask(__name__)
CORS(app)

parser = configparser.ConfigParser()
parser.read("config.ini")
CONFIG = parser
active_sessions = {}

def create_database_connection():
    hostname = CONFIG.get("database", "host")
    user = CONFIG.get("database", "user")
    password = CONFIG.get("database", "password")
    database = CONFIG.get("database", "database")
    ssh_host = CONFIG.get("database", "ssh_host")
    ssh_username = CONFIG.get("database", "ssh_username")
    ssh_password = CONFIG.get("database", "ssh_password")
    remote_bind = CONFIG.get("database", "remote_bind")
    if ssh_host.strip() == "" or ssh_username.strip() == "" or ssh_password.strip() == "":
        return SQLHandler(hostname, user, password, database)
    return SQLHandler(hostname, user, password, database, ssh_host, ssh_username, ssh_password, remote_bind)

def initialize_database():
    sql_handler = create_database_connection()
    sql_handler.create_table("authentication", "id INT AUTO_INCREMENT PRIMARY KEY, authkey VARCHAR(255) UNIQUE")
initialize_database()

    
@app.route("/send_message", methods=["POST"])
def send_message():
    server = create_database_connection()
    cai_key = request.headers.get("X-CAI-KEY")
    character_id = request.headers.get("X-CHARACTER-ID")
    authkey = request.headers.get("Authorization").split(" ")[1]
    if authkey is None or cai_key is None or character_id is None:

        print(authkey, cai_key, character_id)
        abort(400)
        
    if not server.check_row_exists("authentication", "authkey", authkey):
        return abort(401, "Invalid Authentication")
    if authkey not in active_sessions:
        active_sessions[authkey] = ChatSession(cai_key, character_id)
    if character_id != active_sessions[authkey].character_id:
        del active_sessions[authkey]
        active_sessions[authkey] = ChatSession(cai_key, character_id)
    messages = request.json['messages']
    latest_message_content = messages[-1]["content"]
    cai_response_message = active_sessions[authkey].send_message(latest_message_content)
    response_data = {"choices": [{"message": {"content": cai_response_message}}]}
    return jsonify(response_data)    

@app.route("/end_chat_session", methods=["POST"])
def end_chat_session():
    authkey = request.headers.get("Authorization").split(" ")[1]
    if authkey is None:
        abort(400)
    if authkey not in active_sessions:
        abort(400)
    del active_sessions[authkey]
    return jsonify({"message": "Chat session ended."})
app.run()