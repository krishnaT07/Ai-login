import base64
from io import BytesIO
from PIL import Image
from flask import Flask, request, render_template, redirect, url_for
import os
import sqlite3
import face_recognition
from werkzeug.utils import secure_filename
from datetime import datetime
import numpy as np

app = Flask(__name__)

# Define upload folder
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Set maximum file upload size (e.g., 16MB)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32MB

app.config['DATABASE'] = 'database.db'

# Initialize the database (if needed)
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

# Serialize the face encoding to store in the database
def serialize_face_encoding(face_encoding):
    return face_encoding.tobytes()

# Deserialize the face encoding from the database
def deserialize_face_encoding(blob):
    return np.frombuffer(blob, dtype=np.float64)

# Route for the login page
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        captured_image_data = request.form['captured_image']

        if not captured_image_data:
            return "Error: No image captured."

        # Decode the base64 image
        try:
            image_data = base64.b64decode(captured_image_data.split(',')[1])
        except Exception as e:
            return f"Error decoding image: {e}"

        image = Image.open(BytesIO(image_data))
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{username}_login_{timestamp}.png")
        image.save(image_path)

        # Check if username and password are correct
        with sqlite3.connect(app.config['DATABASE']) as conn:
            cursor = conn.execute("SELECT UserID, FaceEmbedding FROM Users WHERE Username = ? AND Password = ?", (username, password))
            user = cursor.fetchone()

            if user:
                # Check face recognition with the captured login image
                uploaded_image = face_recognition.load_image_file(image_path)
                face_encodings = face_recognition.face_encodings(uploaded_image)

                if not face_encodings:
                    return "Error: No face detected in the captured image."

                uploaded_face_embedding = face_encodings[0]

                # Load stored face embedding for comparison (deserialize from BLOB)
                try:
                    stored_face_embedding = deserialize_face_encoding(user[1])
                except Exception as e:
                    return f"Error deserializing face encoding: {e}"

                match = face_recognition.compare_faces([stored_face_embedding], uploaded_face_embedding)

                if match[0]:
                    # Redirect to success page on successful login
                    return redirect(url_for('success', username=username))
                else:
                    return "Face not recognized. Login failed."
            else:
                return "Invalid username or password."
    else:
        return render_template('login.html')

# Route for success page
@app.route('/success/<username>')
def success(username):
   return render_template('web.html', username=username)

# Run the app
if __name__ == '__main__':
    init_db()
    app.run("localhost", port=5001,debug=True)
