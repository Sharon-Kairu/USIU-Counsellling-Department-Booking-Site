from flask import Flask,render_template, request, jsonify,redirect, url_for, session, flash
import json
import os
from flask_cors import CORS 
import logging
import firebase_admin
from firebase_admin import credentials, auth, firestore
import time
import json
import requests


app=Flask(__name__) 
CORS(app)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key') 

logging.basicConfig(level=logging.DEBUG)

# Initialize Firebase Admin SDK
cred = credentials.Certificate('credentials/usiu-counselling-app-firebase-adminsdk-fbsvc-0dee413263.json')
firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()

@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        phone_number = request.form['phoneNumber']
        level = request.form['level']
        role='client'
         # Firebase user sign-up
        try:
            user = auth.create_user(email=email, password=password)
            logging.debug(f"User signed up: {user.email}, UID: {user.uid}")

            # Store user info in Firestore
            db.collection('users').document(user.uid).set({
                'email': user.email,
                'fullName': full_name,  # Store the username provided during signup
                'phoneNumber': phone_number,
                'level':level,
                'role':role,  
                'createdAt': firestore.SERVER_TIMESTAMP
            })
            logging.debug(f"User data saved to Firestore for UID: {user.uid}")

            return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Signup failed for {email}: {e}")
            return render_template('signup.html', error="Signup failed. Please try again.")

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        try:
            # Firebase user retrieval (does NOT authenticate password)
            user = auth.get_user_by_email(email)

            # Fetch user role from Firestore
            user_doc = db.collection('users').document(user.uid).get()
            
            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_role = user_data.get('role')  # Default role: client

                # Store user details in session
                session['user_id'] = user.uid
                session['email'] = user.email
                session['role'] = user_role

                logging.debug(f"User logged in: {user.email}, Role: {user_role}")

                # Redirect based on user role
                if user_role == "client":
                    return redirect(url_for('client'))
                elif user_role == "counsellor":
                    return redirect(url_for('counsellor'))
                else:
                    return redirect(url_for('admin'))
            else:
                flash("User record not found. Please sign up.", "error")
                return redirect(url_for('signup'))

        except firebase_admin.auth.UserNotFoundError:
            flash("Invalid email or user does not exist.", "error")
        except Exception as e:
            logging.error(f"Login failed for {email}: {e}")
            flash("Login failed. Please check your credentials.", "error")

    return render_template('login.html')

# Verify the JWT token received from the Firebase client
@app.route('/verify_token', methods=['POST'])  # Fixed
def verify_token():
    try:
        token = request.json['token']
        decoded_token = auth.verify_id_token(token)
        user_email = decoded_token['email']
        user = auth.get_user_by_email(user_email)  # Get user by email
        user_doc = db.collection('users').document(user.uid).get()  # Fetch user data from Firestore

        if user_doc.exists:
            user_data = user_doc.to_dict()
            user_role = user_data.get('role', 'client')  # Default role: client

            # Store user details in session
            session['user_id'] = user.uid
            session['email'] = user.email
            session['role'] = user_role

            logging.debug(f"User verified and logged in: {user.email}, Role: {user_role}")
            return jsonify(success=True, role=user_role), 200  # Return role in response
        else:
            logging.error(f"User data not found for email: {user.email}")
            return jsonify(success=False, error="User data not found"), 404

    except Exception as e:
        logging.error(f"Token verification failed: {e}")
        return jsonify(success=False, error="Token verification failed"), 401
    

@app.route('/get_quote', methods=['GET'])
def get_quote():
    api_url = 'https://api.api-ninjas.com/v1/quotes'
    headers = {'X-Api-Key': 'viGO7xS/C8BWoM2XTBgoMw==3cts0rEhoKPjl1E0'}

    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == requests.codes.ok:
            quote_data = response.json()[0]  # Extract the first quote from the response
            return jsonify(quote_data)  # Send JSON response to frontend
        else:
            return jsonify({'error': 'Failed to fetch quote'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

        
@app.route('/admin', methods=['GET','POST'])
def admin():
    return render_template('admin.html')

@app.route('/add_a_member', methods=['GET','POST'])
def add_a_member():
    if request.method == 'POST':
        full_name = request.form['fullname']
        email = request.form['email']
        password = request.form['password']
        phone_number = request.form['phoneNumber']
        role=request.form['role']
         # Firebase user sign-up
        try:
            user = auth.create_user(email=email, password=password)
            logging.debug(f"User signed up: {user.email}, UID: {user.uid}")

            # Store user info in Firestore
            db.collection('users').document(user.uid).set({
                'email': user.email,
                'fullName': full_name,  
                'phoneNumber': phone_number,
                'role':role,  
                'createdAt': firestore.SERVER_TIMESTAMP
            })
            logging.debug(f"User data saved to Firestore for UID: {user.uid}")

            return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Signup failed for {email}: {e}")
            return render_template('signup.html', error="Signup failed. Please try again.")

    return render_template('add_a_member.html')


@app.route('/counsellor', methods=['GET','POST'])
def counsellor():
    return render_template('counsellor.html')


@app.route('/previoussessions_counsellor', methods=['GET','POST'])
def previous_sessions_counsellor():
    if 'user_id' not in session:
        logging.debug("User not in session, redirecting to login")
        return redirect(url_for('login'))

    logging.debug(f"User {session['user_id']} in session, rendering previoussessions_counsellor.html")
    return render_template('previoussessions_counsellor.html')


@app.route('/client', methods=['GET','POST'])
def client():
    if 'user_id' not in session:
        logging.debug("User not in session, redirecting to login")
        return redirect(url_for('login'))

    logging.debug(f"User {session['user_id']} in session, rendering client.html")
    return render_template('client.html')

@app.route('/bookappointment', methods=['GET','POST'])
def bookappointment():
    if 'user_id' not in session:
        logging.debug("User not in session, redirecting to login")
        return redirect(url_for('login'))

    logging.debug(f"User {session['user_id']} in session, rendering bookappointment.html")
    return render_template('bookappointment.html')

@app.route('/previoussessions_client', methods=['GET','POST'])
def previous_sessions_client():
    if 'user_id' not in session:
        logging.debug("User not in session, redirecting to login")
        return redirect(url_for('login'))

    logging.debug(f"User {session['user_id']} in session, rendering previoussessions_client.html")
    return render_template('previoussessions_client.html')

@app.route('/view_hours', methods=['GET','POST'])
def view_hours():
    if 'user_id' not in session:
        logging.debug("User not in session, redirecting to login")
        return redirect(url_for('login'))

    logging.debug(f"User {session['user_id']} in session, rendering view_hours.html")
    return render_template('view_hours.html')

@app.route('/change_user_details', methods=['GET','POST'])
def changeuserdetails():
    if 'user_id' not in session:
        logging.debug("User not in session, redirecting to login")
        return redirect(url_for('login'))

    logging.debug(f"User {session['user_id']} in session, rendering change_user_details.html")
    return render_template('change_user_details.html')


if __name__ == '__main__':
    app.run(debug=True)
