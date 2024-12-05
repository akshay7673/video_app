from sqlalchemy import create_engine, text
from flask import Flask, jsonify, request
import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import send_from_directory
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
DB_CONNECTION = os.getenv("DB_CONNECTION")


# Database connection string
DB_CONNECTION = "mssql+pyodbc://adminuser:Password1234!@videoappservereastus2.database.windows.net/videoAppDB?driver=ODBC+Driver+17+for+SQL+Server"

# Create the database engine
engine = create_engine(DB_CONNECTION)

# Flask app initialization
app = Flask(__name__)
SECRET_KEY = "your_secret_key"  # Replace with a secure key

@app.route("/")
def home():
    return "Welcome to the Video App API!"

# JWT token validation decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("x-access-token")
        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = data["username"]
            role = data["role"]
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Token is invalid!"}), 401

        return f(current_user, role, *args, **kwargs)
    return decorated

# User registration endpoint
@app.route("/api/users/register", methods=["POST"])
def register_user():
    data = request.json
    print(f"Incoming Data: {data}")  # Debugging log

    if not data or not all(key in data for key in ("username", "password", "role")):
        return jsonify({"error": "Username, password, and role are required"}), 400

    hashed_password = generate_password_hash(data["password"], method="pbkdf2:sha256")
    print(f"Hashed Password: {hashed_password}")  # Debugging log

    try:
        with engine.connect() as conn:
            transaction = conn.begin()  # Start transaction
            try:
                # Ensure table exists before inserting
                check_table_query = text("""
                    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
                    CREATE TABLE users (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        username NVARCHAR(255) UNIQUE NOT NULL,
                        password NVARCHAR(MAX) NOT NULL,
                        role NVARCHAR(50) NOT NULL
                    )
                """)
                conn.execute(check_table_query)

                # Insert user
                query = text("INSERT INTO users (username, password, role) VALUES (:username, :password, :role)")
                conn.execute(query, {"username": data["username"], "password": hashed_password, "role": data["role"]})
                transaction.commit()  # Commit the transaction
                print("User registered successfully in users table.")  # Debugging log
            except Exception as inner_e:
                transaction.rollback()  # Rollback on error
                print(f"Transaction Error: {inner_e}")  # Log any transaction error
                return jsonify({"error": str(inner_e)}), 500
    except Exception as e:
        print(f"Error during registration: {e}")  # Log any connection or execution error
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "User registered successfully!"}), 201

# User login endpoint
@app.route("/api/users/login", methods=["POST"])
def login_user():
    data = request.json
    print(f"Login Request Data: {data}")  # Log incoming request data

    if not data or not all(key in data for key in ("username", "password")):
        return jsonify({"error": "Username and password are required"}), 400

    try:
        with engine.connect() as conn:
            print("Database connection established.")
            query = text("SELECT * FROM users WHERE username = :username")
            print(f"Executing Query: {query}")  # Debugging log
            user = conn.execute(query, {"username": data["username"]}).fetchone()
            print(f"Database Result: {user}")  # Debugging log

            if not user:
                print("User not found in database.")
                return jsonify({"error": "Invalid username or password"}), 401

            # Convert the result to a dictionary
            user = dict(user._mapping)

            # Check password
            password_from_db = user["password"]
            print(f"Password from DB: {password_from_db}, Entered Password: {data['password']}")  # Debugging log
            if not check_password_hash(password_from_db, data["password"]):
                print("Password hash mismatch.")
                return jsonify({"error": "Invalid username or password"}), 401

            # Generate token
            token = jwt.encode(
                {
                    "username": user["username"],
                    "role": user["role"],
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
                },
                SECRET_KEY,
                algorithm="HS256"
            )
            print("Token generated successfully.")
    except Exception as e:
        print(f"Error during login: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"token": token}), 200



# Endpoint to list all videos
@app.route("/api/videos", methods=["POST"])
@token_required
def upload_video(current_user, role):
    if role != "creator":
        return jsonify({"error": "Only creators can upload videos"}), 403

    data = request.json
    print(f"Video Upload Data: {data}")  # Log incoming request data

    if not data or not all(key in data for key in ("title", "genre")):
        return jsonify({"error": "Title and genre are required"}), 400

    try:
        with engine.connect() as conn:
            transaction = conn.begin()  # Start transaction
            try:
                print("Database connection established for video upload.")  # Debugging log
                query = text("INSERT INTO videos (title, genre, rating, created_at) VALUES (:title, :genre, :rating, GETDATE())")
                conn.execute(query, {
                    "title": data["title"],
                    "genre": data["genre"],
                    "rating": data.get("rating", 0)  # Default rating is 0
                })
                transaction.commit()  # Commit the transaction
                print("Video uploaded successfully to the database.")  # Debugging log
            except Exception as inner_e:
                transaction.rollback()  # Rollback on error
                print(f"Transaction Error during video upload: {inner_e}")
                return jsonify({"error": str(inner_e)}), 500
    except Exception as e:
        print(f"Error during video upload: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"message": "Video uploaded successfully"}), 201



@app.route("/api/videos", methods=["GET"])
def get_videos():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM videos"))
        videos = [dict(row._mapping) for row in result]
    return jsonify({"videos": videos})

# Endpoint to search videos by title or genre
@app.route("/api/videos/search", methods=["GET"])
def search_videos():
    query = request.args.get("q", "").lower()
    if not query:
        return jsonify({"error": "Please provide a search query"}), 400

    with engine.connect() as conn:
        query_text = text("SELECT * FROM videos WHERE LOWER(title) LIKE :query OR LOWER(genre) LIKE :query")
        result = conn.execute(query_text, {"query": f"%{query}%"})
        videos = [dict(row._mapping) for row in result]
    return jsonify({"results": videos})
@app.route("/api/videos/dashboard", methods=["GET"])
def dashboard():
    try:
        with engine.connect() as conn:
            query = text("SELECT * FROM videos ORDER BY created_at DESC")
            result = conn.execute(query)
            videos = [dict(row._mapping) for row in result]
        return jsonify({"latest_videos": videos}), 200
    except Exception as e:
        print(f"Error in Dashboard Endpoint: {e}")
        return jsonify({"error": str(e)}), 500
#Static HTML
@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)
    

if __name__ == "__main__":
    app.run(debug=True)
