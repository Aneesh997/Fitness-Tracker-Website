from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
import requests
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import re
import logging
from logging.handlers import RotatingFileHandler

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Configure logging
log_handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
log_handler.setLevel(logging.ERROR)
app.logger.addHandler(log_handler)

# Configuration
USE_LOCAL_MODEL = True
MODEL_PATH = "/app/model"  # Path where model is mounted in Docker
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Force offline mode
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

# Initialize model safely
try:
    if USE_LOCAL_MODEL:
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_PATH,
            local_files_only=True
        )
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            device_map="auto",
            torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
            local_files_only=True
        )
        app.logger.info(f"Model loaded on {DEVICE.upper()} from local cache")
except Exception as e:
    app.logger.error(f"Model loading failed: {str(e)}")
    USE_LOCAL_MODEL = False
    model = None
    tokenizer = None

def generate_local_response(prompt):
    if not tokenizer or not model:
        return "AI model is not available", False
    
    try:
        inputs = tokenizer(prompt, return_tensors="pt").to(DEVICE)
        
        # Conservative generation parameters for 4GB GPUs
        generation_config = {
            'max_new_tokens': 150,  # Reduced from 200
            'temperature': 0.7,
            'do_sample': True,
            'pad_token_id': tokenizer.eos_token_id,
            'early_stopping': True,
            'num_beams': 1  # Disable beam search to save memory
        }
        
        with torch.inference_mode():
            outputs = model.generate(**inputs, **generation_config)
        
        answer = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return answer.replace(prompt, '').strip(), True
    
    except RuntimeError as e:
        if "CUDA out of memory" in str(e):
            torch.cuda.empty_cache()
            return "The AI is currently overloaded. Please try a shorter question.", False
        return f"Generation error: {str(e)}", False
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
def limit_words(text, max_words):
    """Enforce strict word limit without cutting mid-sentence"""
    words = re.findall(r'\S+|\n', text)
    if len(words) <= max_words:
        return text
    
    last_period = 0
    for i in range(min(max_words, len(words))-1, 0, -1):
        if words[i] in {'.', '!', '?'}:
            last_period = i+1
            break
    
    cutoff = last_period if last_period > max_words*0.7 else max_words
    return ' '.join(words[:cutoff])

def create_connection():
    try:
        return mysql.connector.connect(
            host="host.docker.internal",
            user="root",
            password="1234",
            database="user_db"
        )
    except Error as e:
        app.logger.error(f"Database connection error: {str(e)}")
        raise

def _handle_error(message, status_code, is_json=False):
    """Helper function to handle error responses consistently"""
    if is_json:
        return jsonify({
            'success': False,
            'message': message
        }), status_code
    else:
        flash(message, 'error')
        return render_template('login.html', error=message), status_code

# Core Application Routes
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('home'))
    return render_template('loin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    conn = None
    cursor = None
    
    try:
        if request.method == 'POST':
            # Handle both JSON and form data
            try:
                if request.is_json:
                    data = request.get_json()
                    username = data.get('username', '').strip()
                    password = data.get('password', '').strip()
                else:
                    username = request.form.get('username', '').strip()
                    password = request.form.get('password', '').strip()
                
                if not username or not password:
                    return _handle_error("Username and password are required", 400, request.is_json)
            except Exception as e:
                app.logger.error(f"Request data error: {str(e)}")
                return _handle_error("Invalid request data", 400, request.is_json)

            # Database operations
            try:
                conn = create_connection()
                cursor = conn.cursor(dictionary=True)
                
                cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", 
                             (username, password))
                user = cursor.fetchone()

                if user:
                    session['user'] = user['username']
                    if request.is_json:
                        return jsonify({
                            'success': True,
                            'message': 'Login successful',
                            'redirect': url_for('home')
                        })
                    else:
                        return redirect(url_for('home'))
                else:
                    return _handle_error("Incorrect username or password", 401, request.is_json)

            except Error as db_error:
                app.logger.error(f"Database error: {str(db_error)}")
                return _handle_error("Database operation failed", 500, request.is_json)
            except Exception as e:
                app.logger.error(f"Unexpected error: {str(e)}")
                return _handle_error("Internal server error", 500, request.is_json)

        # GET request handling
        if 'user' in session:
            return redirect(url_for('home'))
        return render_template('login.html')

    finally:
        # Ensure resources are always cleaned up
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                app.logger.error(f"Error closing cursor: {str(e)}")
        if conn:
            try:
                conn.close()
            except Exception as e:
                app.logger.error(f"Error closing connection: {str(e)}")

@app.route('/register', methods=['POST'])
def register():
    conn = None
    cursor = None
    
    try:
        if request.is_json:
            data = request.get_json()
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
        else:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '').strip()

        if not username or not password:
            return _handle_error("Username and password are required", 400, request.is_json)

        try:
            conn = create_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return _handle_error("Username already exists", 400, request.is_json)

            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
            conn.commit()

            session['user'] = username
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'User registered successfully',
                    'redirect': url_for('home')
                }), 201
            return redirect(url_for('home'))

        except Error as e:
            if conn:
                conn.rollback()
            app.logger.error(f"Database error during registration: {str(e)}")
            return _handle_error("Error registering user", 500, request.is_json)
        except Exception as e:
            app.logger.error(f"Unexpected error during registration: {str(e)}")
            return _handle_error("Internal server error", 500, request.is_json)

    finally:
        if cursor:
            cursor.close()
        if conn:
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

# Protected Page Routes
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
    return render_template('pring.html', username=session['user'])

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

@app.route('/diet')
def diet():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('diet.html', username=session.get('user'))

# API Endpoints


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
# ... (other API endpoints for workout, sleep, diet)

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

# AI Coach Route
# Updated AI Coach Route with better error handling and memory management
@app.route('/ai_coach', methods=['GET', 'POST'])
def ai_coach():
    if request.method == 'GET':
        if 'user' not in session:
            return redirect(url_for('login'))
        return render_template('ai.html', username=session.get('user'))
    
    if request.method == 'POST':
        if 'user' not in session:
            return jsonify({'error': 'Please log in to use the AI coach'}), 401
        
        try:
            # Get question from request
            data = request.get_json() if request.is_json else request.form
            question = data.get('question', '').strip()
            
            if not question:
                return jsonify({'error': 'Please enter a question'}), 400

            # Enhanced model loading with fallbacks
            if USE_LOCAL_MODEL:
                try:
                    # Clear GPU cache before generation
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    
                    # Generate response with memory limits
                    answer, success = generate_local_response(question)
                    if success:
                        return jsonify({'answer': answer})
                    
                    # If generation failed, try CPU fallback
                    app.logger.warning(f"GPU generation failed, trying CPU fallback: {answer}")
                    DEVICE = "cpu"
                    model.to('cpu')
                    answer, _ = generate_local_response(question)
                    return jsonify({'answer': answer})
                
                except RuntimeError as e:
                    if "CUDA out of memory" in str(e):
                        torch.cuda.empty_cache()
                        return jsonify({
                            'error': 'The AI is currently overloaded. Please try a shorter question or wait a moment.'
                        }), 503
                    raise

            # If local model fails completely
            return jsonify({
                'error': 'AI service is temporarily unavailable. Please try again later.'
            }), 503

        except Exception as e:
            app.logger.error(f"AI coach error: {str(e)}")
            return jsonify({
                'error': 'An unexpected error occurred. Our team has been notified.'
            }), 500

    return jsonify({'error': 'Method not allowed'}), 405

if __name__ == '__main__':
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    app.run(debug=True, host='0.0.0.0', port=8000)