from flask import Flask, render_template, jsonify, request, send_from_directory, Response, redirect
import requests
import bcrypt
import json
import random


# We might not need to use all these imports now, but they'll definitely come in useful in future.

app = Flask(__name__)

def unauthenticated():
	return jsonify({"error": "unauthenticated"}), 401

def load_accounts():
	with open('accounts.json', 'r') as f:
		j = json.load(f)
		return j

def write_accounts(accounts):
	with open('accounts.json', 'w') as f:
		json.dump(accounts, f)
	return "OK"

def js_create_account(username, password):
	salt = bcrypt.gensalt()
	hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
	accounts = load_accounts()
	if username in accounts:
		return jsonify({'message': 'Username already exists'})
	accounts[username] = {}
	accounts[username]['password_hashed'] = hashed.decode('utf-8')
	ids = []
	for account in accounts:
		ids.append(accounts[account].get('id'))
	accounts[username]['id'] = generate_user_id(ids)
	accounts[username]['friends'] = []
	accounts[username]['pending'] = []
	write_accounts(accounts)
	return jsonify({'message': 'Account created successfully'})

def get_username(id):
	accounts = load_accounts()
	for account in accounts:
		if accounts[account]['id'] == id:
			return account
	return None

def get_id(username):
	accounts = load_accounts()
	for account in accounts:
		if account == username:
			return accounts[account]['id']
	return None

def check_login(username, password):
	accounts = load_accounts()
	if not username in accounts:
		return jsonify({'message': 'Account not found'})
	if bcrypt.checkpw(password.encode('utf-8'), accounts[username]['password_hashed'].encode('utf-8')):
		return jsonify({'message': 'Login successful'})
	else:
		return jsonify({'message': 'Invalid password'})

def authenticate(username, password):
	accounts = load_accounts()
	if not username in accounts:
		return False
	if bcrypt.checkpw(password.encode('utf-8'), accounts[username]['password_hashed'].encode('utf-8')):
		return True
	else:
		return False

def get_chat(chat_id):
	try:
		with open(f"chats/{chat_id}.json", 'r') as f:
			return json.load(f)
	except:
		return None

def write_chat(chat_id, data):
	with open(f"chats/{chat_id}.json", 'w') as f:
		json.dump(chat, f)

def get_participants(chat):
	participants = []
	for participant in chat["participants"]:
		participants.append(chat["participants"][participant]["id"])
	return participants

def generate_id(messages):
	ids = []
	for message in messages:
		ids.append(message['id'])
	id = ''.join(str(random.randint(0,9)) for _ in range(8))
	while id in ids:
		id = ''.join(str(random.randint(0,9)) for _ in range(8))
	return id

def generate_user_id(ids):
	id = ''.join(str(random.randint(0,9)) for _ in range(12))
	while id in ids:
		id = ''.join(str(random.randint(0,9)) for _ in range(12))
	return id
	

def send_message(chat_id, author_id, content):
	chat = get_chat(chat_id)
	if chat == None:
		return jsonify({"id":None})
	if not author_id in get_participants(chat):
		return jsonify({"id":None})
	messages = chat["messages"]
	id = generate_id(messages)
	messages.append({
		"id":id,
		"author":author_id,
		"content":content
	})
	chat["messages"] = messages
	write_chat(chat_id, chat)
	return jsonify({"id":id})

def is_allowed(username, password, chat_id):
	return authenticate(username, password) and get_id(username) in get_participants(get_chat(chat_id))

def get_user_data(id):
	accounts = load_accounts()
	for account in accounts:
		if accounts[account]['id'] == id:
			them = accounts[account]
			del them["password_hashed"]
			them["username"] = get_username(id)
			return jsonify(them)
	return jsonify({"error":"user not found"}), 404

def send_friend_request(username, password, recipient_id):
	if not authenticate(username, password):
		return unauthenticated()
	else:
		if not get_id(username) == recipient_id or recipient_id in get_user_data(get_id(username))["friends"]:
			recipient = get_username(recipient_id)
			accounts = load_accounts()
			accounts[recipient]["pending"].append(get_id(username))
			write_accounts(accounts)
		return jsonify({"message":"request sent"})

def accept_friend_request(username, password, friender_id):
	if not authenticate(username, password):
		return unauthenticated()
	else:
		accounts = load_accounts()
		accounts[username]["pending"] = [item for item in accounts[username]["pending"] if item != friender_id]
		accounts[username]["friends"].append(friender_id)
		accounts[get_username(friender_id)]["friends"].append(get_id(username))
		write_accounts(accounts)
		return jsonify({"message": "OK"})

def reject_friend_request(username, password, friender_id):
	if not authenticate(username, password):
		return unauthenticated()
	else:
		accounts = load_accounts()
		accounts[username]["pending"] = [item for item in accounts[username]["pending"] if item != friender_id]
		write_accounts(accounts)
		return jsonify({"message": "OK"})

def unfriend(username, password, friend_id):
	if not authenticate(username, password):
		return unauthenticated()
	else:
		accounts = load_accounts()
		l = accounts[get_username(friend_id)]["friends"]
		l = [item for item in l if item != get_id(username)]
		accounts[get_username(friend_id)]["friends"] = l
		l2 = accounts[username]["friends"]
		l2 = [item for item in l2 if item != friend_id]
		accounts[username]["friends"] = l2
		write_accounts(accounts)

@app.route('/api/users/<id>/unfriend', methods=['POST'])
def unfriend_friend_api(id):
	b = request.get_json(force=True)
	return unfriend(b["username"], b["password"], id)

@app.route('/api/users/<id>/accept_request', methods=['POST'])
def accept_friend_request_api(id):
	b = request.get_json(force=True)
	return accept_friend_request(b["username"], b["password"], id)

@app.route('/api/users/<id>/reject_request', methods=['POST'])
def reject_friend_request_api(id):
	b = request.get_json(force=True)
	return reject_friend_request(b["username"], b["password"], id)

@app.route('/api/users/<id>/send_request', methods=['POST'])
def send_request_friend_api(id):
	b = request.get_json(force=True)
	return send_friend_request(b["username"], b["password"], id)

@app.route('/api/get_user_id/<username>')
def get_user_by_id_api(username):
	return jsonify({"id":get_id(username)})


@app.route('/api/chats/<id>', methods=['POST'])
def api_chat_id(id):
	b = request.get_json(force=True)
	if is_allowed(b['username'], b['password'], id):
		return get_chat(id)
	else:
		return unauthenticated()

@app.route('/api/chats/<id>/post_message', methods=['POST'])
def post_message_api(id):
	b = request.get_json(force=True)
	if is_allowed(b['username'], b['password'], id):
		return send_message(id, get_id(b['username']), b['content'])
	else:
		return unauthenticated()

@app.route('/api/users/<id>')
def api_users(id):
	return get_user_data(id)

@app.route('/api/search_users/')
def search_users_api():
	try:
		query = request.args.get('q').lower()
		limit = min(20, int(request.args.get('limit')))
	except:
		return jsonify({'error':'limit must be an integer'}), 400
	if not query or not limit:
		return jsonify({'error':'missing query or limit'}), 400
	accounts = load_accounts()
	results = []
	for account in accounts:
		if query in str(account):
			results.append(str(account))
	results = results[:limit]
	return jsonify({'results':results})
	

@app.route('/')
def index():
	return redirect('/login') # We can add an actual homepage later

@app.route('/dashboard')
def dashboard():
	return render_template("dashboard.html")

@app.route('/reset_password')
def reset_password():
	return redirect('/in_progress')

@app.route('/in_progress')
def in_progress():
	return "<h1>Site in Progress</h1><p>This part of the site is still under construction. Check back soon!</p>"

@app.route('/login')
def login():
	return render_template('login.html')

@app.route('/register')
def register():
	return render_template('register.html')

@app.route('/api/create_account', methods=['GET', 'POST'])
def create_account():
	j = request.get_json()
	username = j['username']
	password = j['password']
	return js_create_account(username, password)

@app.route('/api/login', methods=['GET', 'POST'])
def verify_login():
	j = request.get_json()
	username = j['username']
	password = j['password']
	return check_login(username, password)

if __name__ == '__main__':
	app.run(debug=True, port='1234', host='0.0.0.0')
