from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure random key in production

# Database connection function
def create_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="user_db"
    )

# Home route - redirects to login if not authenticated
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

# Login route - handles both GET and POST
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle AJAX login request
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            # Handle form submission
            username = request.form.get('username')
            password = request.form.get('password')

        conn = create_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
            user = cursor.fetchone()

            if user:
                session['user'] = user['username']
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': 'Login successful',
                        'redirect': url_for('home')
                    }), 200
                else:
                    return redirect(url_for('home'))
            else:
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'message': 'Incorrect username or password'
                    }), 401
                else:
                    return render_template('login.html', error='Incorrect username or password')
        except Error as e:
            print(f"Database error: {e}")
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Database error'
                }), 500
            else:
                return render_template('login.html', error='Database error')
        finally:
            cursor.close()
            conn.close()
    else:
        # GET request - show login page
        if 'user' in session:
            return redirect(url_for('home'))
        return render_template('login.html')

# Registration route
@app.route('/register', methods=['POST'])
def register():
    if request.is_json:
        data = request.get_json()
        username = data['username']
        password = data['password']
    else:
        username = request.form['username']
        password = request.form['password']

    conn = create_connection()
    cursor = conn.cursor()

    try:
        # Check if username exists
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Username already exists'
                }), 400
            else:
                return render_template('login.html', error='Username already exists')

        # Insert new user
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'User registered successfully'
            }), 201
        else:
            session['user'] = username
            return redirect(url_for('home'))
    except Error as e:
        print(f"Database error: {e}")
        conn.rollback()
        if request.is_json:
            return jsonify({
                'success': False,
                'message': 'Error registering user'
            }), 500
        else:
            return render_template('login.html', error='Error registering user')
    finally:
        cursor.close()
        conn.close()

# Home page route (protected)
@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['user'])

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/about')
def about():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('about.html', username=session['user'])

@app.route('/courses')
def courses():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('courses.html', username=session['user'])

@app.route('/pricing')
def pricing():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('pricing.html', username=session['user'])

@app.route('/contact')
def contact():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('contact.html', username=session.get('user'))

@app.route('/services')
def services():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('services.html', username=session.get('user'))

@app.route('/blog_details')
def blog_details():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('blog_details.html', username=session.get('user'))

@app.route('/elements')
def elements():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('elements.html', username=session.get('user'))

@app.route('/contact_submit', methods=['POST'])
def contact_submit():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Get form data
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    message = request.form.get('message')
    
    # Here you would typically:
    # 1. Validate the form data
    # 2. Save to database or send email
    # 3. Return a response
    
    # For now, we'll just print the data and redirect
    print(f"Contact form submitted: {name}, {email}, {subject}, {message}")
    flash('Your message has been sent successfully!', 'success')
    return redirect(url_for('contact'))

if __name__ == '__main__':
    app.run(debug=True)