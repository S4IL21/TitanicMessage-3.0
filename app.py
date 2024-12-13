from flask import Flask, render_template, jsonify, request, send_from_directory, Response, redirect
import requests
import bcrypt
import json

# We might not need to use all these imports now, but they'll definitely come in useful in future.

app = Flask(__name__)
app.url_map.strict_slashes = False # Making sure 'site/page' is equal to 'site/page/'

@app.route('/')
def index():
	return redirect('/login') # We can add an actual homepage later

@app.route('/login')
def login():
	return render_template('login.html')

@app.route('/register')
def register():
	return render_template('register.html')

def load_accounts():
	with open('accounts.json', 'r') as f:
		j = json.load(f)
		return j

def write_accounts(accounts):
	with open('accounts.json', 'w') as f:
		json.dump(accounts, f, indent=4)
	return "OK"

def create_account(username, password):
	salt = bcrypt.gensalt()
	hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
	accounts = load_accounts()
	if username in accounts:
		return "Username already exists"
	accounts[username] = {}
	accounts[username]['password_hashed'] = hashed
	return write_accounts(accounts)

def check_login(username, password):
	accounts = load_accounts()
	if not username in accounts:
		return "Account not found"
	return bcrypt.checkpw(password.encode('utf-8'), accounts[username]['password'].encode('utf-8'))

@app.route('/endpoint/create_account', methods=['POST'])
def create_account():
	j = request.get_json()
	username = j['username']
	password = j['password']
	return create_account(username, password)

@app.route('/endpoint/login', methods=['POST'])
def verify_login():
	j = request.get_json()
	username = j['username']
	password = j['password']
	return check_login(username, password)

if __name__ == '__main__':
	app.run(debug=True, port='1234', host='0.0.0.0')
