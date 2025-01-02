from flask import Flask, request, jsonify, render_template
import requests
from ratelimit import limits, sleep_and_retry

TMDB_BASE_URL = 'https://api.themoviedb.org/3'

# Read API key from the text file
with open('D:/secret/tmdb_api_key.txt', 'r') as file:
    API_KEY = file.read().strip()

app = Flask(__name__)

# Rate limit configuration
REQUESTS_PER_SECOND = 35
SECONDS = 1

@sleep_and_retry
@limits(calls=REQUESTS_PER_SECOND, period=SECONDS)
def fetch_movie_runtime(movie_id):
    """Fetch the runtime and revenue for a specific movie by its ID."""
    url = f"{TMDB_BASE_URL}/movie/{movie_id}?api_key={API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        movie_details = response.json()
        return movie_details.get('runtime', 'Unknown'), movie_details.get('revenue', 0)
    return 'Unknown', 0

@sleep_and_retry
@limits(calls=REQUESTS_PER_SECOND, period=SECONDS)
def fetch_movies(genre=None, page=1, sort='popularity.desc'):
    """Fetch movies from TMDB API based on genre, page, and sort."""
    genre_param = f"&with_genres={genre}" if genre else ""
    
    url = f"{TMDB_BASE_URL}/discover/movie?api_key={API_KEY}{genre_param}&page={page}&sort_by={sort}&per_page=12"
    
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/recommendations', methods=['GET'])
def get_movie_recommendations():
    genre = request.args.get('genre')
    page = int(request.args.get('page', 1))
    sort = request.args.get('sort', 'popularity.desc')

    # Attempt fetching movies with the provided genre first
    data = fetch_movies(genre=genre, page=page, sort=sort)
    
    # If no movies are returned, try another genre
    if not data or 'results' not in data or len(data['results']) == 0:
        # List of possible genres to try (this is a small sample)
        genres_to_try = ['28', '12', '16', '35', '80']  # Action, Adventure, Animation, Comedy, Crime
        
        for genre_id in genres_to_try:
            data = fetch_movies(genre=genre_id, page=page, sort=sort)
            if data and 'results' in data and len(data['results']) > 0:
                break  # Found movies, stop trying other genres
    
    if not data or 'results' not in data or len(data['results']) == 0:
        return jsonify({"error": "Failed to fetch data from TMDB, no movies found"}), 500

    movies = []
    for movie in data['results']:
        runtime, revenue = fetch_movie_runtime(movie['id'])  # Fetch runtime and revenue for each movie
        
        # Only add movies to the list if the revenue is greater than 5000 and runtime > 30 minutes
        if (runtime != 'Unknown' and runtime > 30):
            movies.append({
                'id': movie['id'],
                'title': movie['title'],
                'overview': movie['overview'],
                'release_date': movie.get('release_date', 'Unknown'),
                'runtime': runtime,
                'rating': movie['vote_average'],
                'poster_path': f"https://image.tmdb.org/t/p/w200{movie['poster_path']}" if movie.get('poster_path') else None
            })

    total_pages = data['total_pages']
    return render_template('index.html', movies=movies, current_page=page, total_pages=total_pages, genre=genre, sort=sort)

if __name__ == '__main__':
    app.run(debug=True)
