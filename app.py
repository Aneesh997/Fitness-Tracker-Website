from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
from datetime import datetime  # Added this import

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def create_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
        database="user_db"
    )

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
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
        if 'user' in session:
            return redirect(url_for('home'))
        return render_template('login.html')

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
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Username already exists'
                }), 400
            else:
                return render_template('login.html', error='Username already exists')

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

@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['user'])

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

@app.route('/tracking')
def tracking():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('tracking.html', username=session.get('user'))

@app.route('/sleep')
def sleep():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('sleep.html', username=session.get('user'))

@app.route('/workout')
def workout():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('workout.html', username=session.get('user'))

# Workout API Endpoints
@app.route('/api/workouts', methods=['GET'])
def get_workout_plans():
    try:
        workouts = [
            {"id": 1, "name": "Running", "calories_per_min": 10, "image": "running.jpg"},
            {"id": 2, "name": "Jogging", "calories_per_min": 8, "image": "jogging.jpg"},
            {"id": 3, "name": "Treadmill", "calories_per_min": 7, "image": "treadmill.jpg"},
            {"id": 4, "name": "Cycling", "calories_per_min": 6, "image": "cycling.jpg"},
            {"id": 5, "name": "Swimming", "calories_per_min": 9, "image": "swimming.jpg"},
            {"id": 6, "name": "Weight Training", "calories_per_min": 5, "image": "weights.jpg"},
            {"id": 7, "name": "Yoga", "calories_per_min": 3, "image": "yoga.jpg"},
            {"id": 8, "name": "HIIT", "calories_per_min": 12, "image": "hiit.jpg"},
            {"id": 9, "name": "Rowing", "calories_per_min": 8, "image": "rowing.jpg"},
            {"id": 10, "name": "Stair Climbing", "calories_per_min": 9, "image": "stairs.jpg"}
        ]
        return jsonify({'success': True, 'workouts': workouts})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/workout', methods=['POST'])
def save_workout():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    username = session['user']
    workout_id = data['workout_id']
    workout_name = data['workout_name']
    duration = data['duration']
    calories = data['calories']
    date = data.get('date') or datetime.now().strftime('%Y-%m-%d')

    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO workout_data 
            (username, workout_id, workout_name, duration, calories, date) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (username, workout_id, workout_name, duration, calories, date))
        conn.commit()
        return jsonify({
            'success': True, 
            'message': 'Workout saved successfully',
            'id': cursor.lastrowid
        })
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/workout', methods=['GET'])
def get_workout_data():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    username = session['user']
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, workout_id, workout_name, duration, calories, date 
            FROM workout_data 
            WHERE username = %s AND date = %s
            ORDER BY id DESC
        """, (username, date))
        workout_data = cursor.fetchall()
        return jsonify({'success': True, 'data': workout_data})
    except Error as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/workout/<int:id>', methods=['DELETE'])
def delete_workout_entry(id):
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    username = session['user']
    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM workout_data 
            WHERE id = %s AND username = %s
        """, (id, username))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({
                'success': False, 
                'message': 'Entry not found or not owned by user'
            }), 404
            
        return jsonify({
            'success': True, 
            'message': 'Workout entry deleted successfully'
        })
    except Error as e:
        conn.rollback()
        return jsonify({
            'success': False, 
            'message': f'Error deleting workout entry: {str(e)}'
        }), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/sleep', methods=['POST'])
def save_sleep_data():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    username = session['user']
    total_sleep = data['total_sleep']
    deep_sleep = data['deep_sleep']
    normal_sleep = data['normal_sleep']
    light_sleep = data['light_sleep']
    awake_time = data['awake_time']
    date = data.get('date')  # Optional date parameter

    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO sleep_data 
            (username, total_sleep, deep_sleep, normal_sleep, light_sleep, awake_time, date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, total_sleep, deep_sleep, normal_sleep, light_sleep, awake_time, date))
        conn.commit()
        return jsonify({'success': True, 'message': 'Sleep data saved successfully'})
    except Error as e:
        conn.rollback()
        return jsonify({'success': False, 'message': 'Error saving sleep data'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/sleep', methods=['GET'])
def get_sleep_data():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    username = session['user']
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT * FROM sleep_data 
            WHERE username = %s 
            ORDER BY date DESC, id DESC
        """, (username,))
        sleep_data = cursor.fetchall()
        return jsonify({'success': True, 'data': sleep_data})
    except Error as e:
        return jsonify({'success': False, 'message': 'Error fetching sleep data'}), 500
    finally:
        cursor.close()
        conn.close()


# ... (keep all your existing routes until the diet section) ...

@app.route('/diet')
def diet():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('diet.html', username=session.get('user'))

@app.route('/api/diet', methods=['POST'])
def save_diet_data():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    data = request.get_json()
    username = session['user']
    dish_name = data['dish_name']
    protein = data['protein']
    carbs = data['carbs']
    calories = data['calories']
    fat = data['fat']
    date = data.get('date') or datetime.now().strftime('%Y-%m-%d')

    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO diet_data 
            (username, dish_name, protein, carbs, calories, fat, date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (username, dish_name, protein, carbs, calories, fat, date))
        conn.commit()
        return jsonify({
            'success': True, 
            'message': 'Diet data saved successfully',
            'id': cursor.lastrowid
        })
    except Error as e:
        conn.rollback()
        return jsonify({
            'success': False, 
            'message': f'Error saving diet data: {str(e)}'
        }), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/diet', methods=['GET'])
def get_diet_data():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    username = session['user']
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    conn = create_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, dish_name, protein, carbs, fat, calories, date 
            FROM diet_data 
            WHERE username = %s AND date = %s
            ORDER BY id DESC
        """, (username, date))
        diet_data = cursor.fetchall()
        return jsonify({'success': True, 'data': diet_data})
    except Error as e:
        return jsonify({
            'success': False, 
            'message': f'Error fetching diet data: {str(e)}'
        }), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/diet/<int:id>', methods=['DELETE'])
def delete_diet_entry(id):
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    username = session['user']
    conn = create_connection()
    cursor = conn.cursor()

    try:
        # First verify the entry belongs to the user
        cursor.execute("""
            DELETE FROM diet_data 
            WHERE id = %s AND username = %s
        """, (id, username))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({
                'success': False, 
                'message': 'Entry not found or not owned by user'
            }), 404
            
        return jsonify({
            'success': True, 
            'message': 'Diet entry deleted successfully'
        })
    except Error as e:
        conn.rollback()
        return jsonify({
            'success': False, 
            'message': f'Error deleting diet entry: {str(e)}'
        }), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/dishes', methods=['GET'])
def get_dishes():
    try:
        dishes = [
            {"name": "Grilled Chicken", "protein": 31, "carbs": 0, "calories": 165, "fat": 3.6, "image": "Grilled Chicken.jpg"},
            {"name": "Salmon Fillet", "protein": 25, "carbs": 0, "calories": 206, "fat": 13, "image": "Salmon Fillet.jpg"},
            {"name": "Vegetable Stir Fry", "protein": 4, "carbs": 12, "calories": 120, "fat": 7, "image": "Vegitable Stir Fry.png"},
            {"name": "Greek Yogurt", "protein": 10, "carbs": 9, "calories": 100, "fat": 0.4, "image": "Greek Yogurt.jpg"},
            {"name": "Oatmeal", "protein": 5, "carbs": 27, "calories": 150, "fat": 2.5, "image": "Oatmeal.jpg"},
            {"name": "Quinoa Salad", "protein": 8, "carbs": 39, "calories": 222, "fat": 4, "image": "Quinoa Salad.jpg"},
            {"name": "Avocado Toast", "protein": 4, "carbs": 25, "calories": 220, "fat": 15, "image": "Avocado Toast.jpg"},
            {"name": "Egg White Omelette", "protein": 18, "carbs": 2, "calories": 100, "fat": 4, "image": "Egg White Omelette.jpg"},
            {"name": "Sweet Potato", "protein": 2, "carbs": 27, "calories": 114, "fat": 0.1, "image": "Sweet Potato.jpeg"},
            {"name": "Tuna Salad", "protein": 29, "carbs": 5, "calories": 179, "fat": 6, "image": "Tuna Salad.jpg"},
            {"name": "Brown Rice", "protein": 5, "carbs": 45, "calories": 215, "fat": 1.8, "image": "Brown Rice.jpg"},
            {"name": "Protein Shake", "protein": 24, "carbs": 8, "calories": 160, "fat": 2, "image": "Protein Shake.jpg"}
        ]
        return jsonify({'success': True, 'dishes': dishes})
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error fetching dishes: {str(e)}'
        }), 500

# Add this new route to your existing app.py
@app.route('/contact_submit', methods=['POST'])
def contact_submit():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        ip_address = request.remote_addr

        conn = create_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO contact_submissions 
                (name, email, subject, message, ip_address) 
                VALUES (%s, %s, %s, %s, %s)
            """, (name, email, subject, message, ip_address))
            conn.commit()
            
            flash('Your message has been sent successfully! We will get back to you soon.', 'success')
            return redirect(url_for('contact'))
            
        except Error as e:
            conn.rollback()
            flash('There was an error submitting your message. Please try again later.', 'error')
            return redirect(url_for('contact'))
            
        finally:
            cursor.close()
            conn.close()
if __name__ == '__main__':
    app.run(debug=True)