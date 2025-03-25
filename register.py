import base64
from io import BytesIO
from PIL import Image
from flask import Flask, request, render_template, redirect, url_for
import os
import sqlite3
import face_recognition
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)

# Define upload folder
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

# Set maximum file upload size (e.g., 16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

app.config['DATABASE'] = 'database.db'


# Initialize database
def init_db():
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS Users (
                UserID INTEGER PRIMARY KEY AUTOINCREMENT,
                Username TEXT NOT NULL UNIQUE,
                Password TEXT NOT NULL,
                FaceEmbedding BLOB NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS Images (
                ImageID INTEGER PRIMARY KEY AUTOINCREMENT,
                UserID INTEGER,
                ImagePath TEXT NOT NULL,
                FOREIGN KEY (UserID) REFERENCES Users(UserID)
            )
        ''')


@app.route('/')
def index():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    
    image_path = None  # Initialize the variable to store image path

    # Handle file upload
    if 'image' in request.files:
        image = request.files['image']
        if image:
            filename = secure_filename(image.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            unique_filename = f"{username}_{timestamp}_{filename}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            print(f"Saving uploaded image to: {image_path}")
            image.save(image_path)

    # Handle captured image from camera
    elif 'captured_image' in request.form and request.form['captured_image']:
        captured_image_data = request.form['captured_image']
        image_data = base64.b64decode(captured_image_data.split(',')[1])
        image = Image.open(BytesIO(image_data))
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{username}_captured.png")
        print(f"Saving captured image to: {image_path}")
        image.save(image_path)

    else:
        return "Error: No image uploaded or captured."

    # Register the user with the saved image
    if image_path and register_user(username, password, image_path):
        # Redirect to the success page after successful registration
        return redirect(url_for('success', username=username))
    else:
        return "No face detected in the image."


@app.route('/success/<username>')
def success(username):
    return render_template('register.html', username=username)


def register_user(username, password, image_path):
    # Load the image and generate face embedding
    image = face_recognition.load_image_file(image_path)
    face_encodings = face_recognition.face_encodings(image)
    if not face_encodings:
        return False  # No face detected
    face_embedding = face_encodings[0].tobytes()

    # Save user to database
    with sqlite3.connect(app.config['DATABASE']) as conn:
        conn.execute('''
            INSERT INTO Users (Username, Password, FaceEmbedding)
            VALUES (?, ?, ?)
        ''', (username, password, face_embedding))
    return True


if __name__ == '__main__':
    init_db()
    app.run("localhost", port=5000)
