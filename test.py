from flask import Flask, jsonify, request

app = Flask(__name__)

# Sample video data for now
videos = [
    {"id": 1, "title": "Intro to Python", "genre": "Education", "rating": 4.5},
    {"id": 2, "title": "Flask for Beginners", "genre": "Programming", "rating": 4.7},
]

@app.route("/")
def home():
    return "Welcome to the Video App API!"

# Endpoint to list all videos
@app.route("/api/videos", methods=["GET"])
def get_videos():
    return jsonify({"videos": videos})

# Endpoint to search videos by title or genre
@app.route("/api/videos/search", methods=["GET"])
def search_videos():
    query = request.args.get("q", "").lower()
    if not query:
        return jsonify({"error": "Please provide a search query"}), 400

    # Search videos by title or genre
    results = [video for video in videos if query in video["title"].lower() or query in video["genre"].lower()]
    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(debug=True)
