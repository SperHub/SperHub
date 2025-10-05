# home.py
# Micro "FriendHub / MockHub" - single-file Flask app
# Look: Pornhub-like (noir / orange) but SAFE content only.
# Requirements: Flask, werkzeug, pillow (optional).
# Optional: ffmpeg installed to extract thumbnails.
#
# Usage:
#   pip install Flask pillow
#   (install ffmpeg if you want thumbnails)
#   python home.py
# Then open http://127.0.0.1:5000

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///friendhub.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# -------------------------------------------------
# Base HTML
# -------------------------------------------------
BASE_TEMPLATE = """
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title or 'FriendHub' }}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  :root {
    --bg: #0f0f12;
    --card: #141418;
    --muted: #9aa0a6;
    --accent: #ff6600;
    --accent-2: #ff9a2a;
    --border: #222;
    --text: #e9ecef;
  }
  body { background: var(--bg); color: var(--text); }
  .navbar { background: #000; border-bottom: 1px solid var(--border); }
  .brand { font-weight:800; color: var(--accent); font-size:1.4rem }
  .search-input { background:#0b0b0d; color:#eee; border:1px solid var(--border); }
  .card-dark { background: var(--card); border:1px solid var(--border); color: var(--text); }
  .thumb { height:160px; object-fit:cover; width:100%; background:#111; }
  .video-title { font-size:0.95rem; font-weight:700; margin-bottom:0.2rem; color:var(--text); }
  .meta { color:var(--muted); font-size:0.85rem; }
  .btn-accent { background: linear-gradient(90deg,var(--accent),var(--accent-2)); border: none; color: #000; font-weight:700; }
  .logo { display:flex; align-items:center; gap:8px; }
  .logo-dot { width:12px; height:12px; background:var(--accent); border-radius:2px; display:inline-block; margin-right:6px;}
  a, a:hover { color: inherit; text-decoration: none; }
  footer { color:var(--muted); padding:20px 0; }
  .category-badge { background: rgba(255,255,255,0.04); padding:3px 8px; border-radius:12px; margin-right:6px; font-size:0.8rem; }
  .small-muted { color: var(--muted); font-size:0.85rem; }
</style>
</head>
<body>
<nav class="navbar navbar-dark">
  <div class="container-fluid">
    <div class="d-flex align-items-center">
      <a class="navbar-brand d-flex align-items-center gap-2" href="{{ url_for('index') }}">
        <span class="logo-dot"></span>
        <span class="brand">Friend<span style="color:var(--text); font-weight:400">Hub</span></span>
      </a>
    </div>

    <form class="d-flex" action="{{ url_for('index') }}" method="get" style="max-width:540px; flex:1; margin:0 16px;">
      <input name="q" class="form-control me-2 search-input" type="search" placeholder="Rechercher (titre, description...)" value="{{ request.args.get('q','') }}">
      <select name="category" class="form-select ms-2" style="max-width:160px; background:#0b0b0d; color:#fff; border:1px solid var(--border);">
        <option value="">Toutes</option>
        <option value="Funny">Funny</option>
        <option value="Gameplay">Gameplay</option>
        <option value="Vlog">Vlog</option>
        <option value="Music">Music</option>
        <option value="Prank">Prank</option>
      </select>
      <button class="btn btn-accent ms-2" type="submit">Rechercher</button>
    </form>

    <div class="d-flex align-items-center">
      {% if session.get('user') %}
        <a class="btn btn-sm btn-outline-light me-2" href="{{ url_for('profile', username=session.get('user')) }}">{{ session.get('user') }}</a>
        <a class="btn btn-sm btn-outline-light me-2" href="{{ url_for('upload') }}">Uploader</a>
        <a class="btn btn-sm btn-outline-light" href="{{ url_for('logout') }}">Déconnexion</a>
      {% else %}
        <a class="btn btn-sm btn-outline-light me-2" href="{{ url_for('login') }}">Se connecter</a>
        <a class="btn btn-sm btn-accent" href="{{ url_for('register') }}">Inscription</a>
      {% endif %}
    </div>
  </div>
</nav>

<div class="container-fluid mt-3">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat,msg in messages %}
        <div class="alert alert-{{ 'success' if cat=='success' else 'warning' }} py-2">{{ msg }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}
  {{ content|safe }}
</div>

<footer class="container">
  <hr style="border-color:var(--border)">
  <div class="d-flex justify-content-between">
    <div class="small-muted">Made for fun • Look & feel inspiré mais sans contenu explicite</div>
    <div class="small-muted">Open-source demo</div>
  </div>
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# -------------------------------------------------
# Models
# -------------------------------------------------
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120))
    category = db.Column(db.String(80))
    thumbnail = db.Column(db.String(200))
    uploader = db.Column(db.String(80))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(80))

with app.app_context():
    db.create_all()

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.route("/")
def index():
    q = request.args.get("q", "")
    category = request.args.get("category", "")
    videos = Video.query
    if q:
        videos = videos.filter(Video.title.ilike(f"%{q}%"))
    if category:
        videos = videos.filter_by(category=category)
    videos = videos.all()

    content = "<h4>Vidéos populaires</h4><div class='row mt-2'>"
    for v in videos:
        content += f"""
        <div class='col-sm-6 col-md-4 col-lg-3 mb-3'>
            <div class='card card-dark'>
                <img src='{v.thumbnail or "https://placehold.co/400x225"}' class='thumb'>
                <div class='p-2'>
                    <div class='video-title'>{v.title}</div>
                    <div class='meta'>{v.category} • {v.uploader}</div>
                </div>
            </div>
        </div>
        """
    content += "</div>"
    return render_template_string(BASE_TEMPLATE, title="Accueil", content=content, videos=videos)

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not session.get("user"):
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        thumbnail = request.form["thumbnail"]
        db.session.add(Video(title=title, category=category, thumbnail=thumbnail, uploader=session["user"]))
        db.session.commit()
        flash("Vidéo ajoutée avec succès !", "success")
        return redirect(url_for("index"))

    content = """
    <h4>Uploader une vidéo</h4>
    <form method="post" class="mt-3">
        <input name="title" class="form-control mb-2" placeholder="Titre" required>
        <input name="category" class="form-control mb-2" placeholder="Catégorie">
        <input name="thumbnail" class="form-control mb-2" placeholder="URL miniature">
        <button class="btn btn-accent" type="submit">Uploader</button>
    </form>
    """
    return render_template_string(BASE_TEMPLATE, title="Upload", content=content)

@app.route("/video/<int:video_id>")
def video_page(video_id):
    v = Video.query.get_or_404(video_id)
    content = f"""
    <h3>{v.title}</h3>
    <img src="{v.thumbnail}" class="img-fluid mb-3">
    <p>Catégorie: {v.category}</p>
    <p>Ajoutée par <strong>{v.uploader}</strong></p>
    """
    return render_template_string(BASE_TEMPLATE, title=v.title, content=content)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"], password=request.form["password"]).first()
        if user:
            session["user"] = user.username
            flash("Connexion réussie", "success")
            return redirect(url_for("index"))
        else:
            flash("Identifiants invalides", "error")
    content = """
    <h4>Connexion</h4>
    <form method="post" class="mt-3" style="max-width:400px;">
        <input name="username" class="form-control mb-2" placeholder="Nom d'utilisateur">
        <input name="password" type="password" class="form-control mb-2" placeholder="Mot de passe">
        <button class="btn btn-accent w-100">Se connecter</button>
    </form>
    """
    return render_template_string(BASE_TEMPLATE, title="Connexion", content=content)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if User.query.filter_by(username=request.form["username"]).first():
            flash("Nom d'utilisateur déjà pris", "error")
        else:
            db.session.add(User(username=request.form["username"], password=request.form["password"]))
            db.session.commit()
            flash("Compte créé ! Vous pouvez maintenant vous connecter.", "success")
            return redirect(url_for("login"))
    content = """
    <h4>Inscription</h4>
    <form method="post" class="mt-3" style="max-width:400px;">
        <input name="username" class="form-control mb-2" placeholder="Nom d'utilisateur">
        <input name="password" type="password" class="form-control mb-2" placeholder="Mot de passe">
        <button class="btn btn-accent w-100">Créer un compte</button>
    </form>
    """
    return render_template_string(BASE_TEMPLATE, title="Inscription", content=content)

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Déconnecté avec succès", "success")
    return redirect(url_for("index"))

@app.route("/profile/<username>")
def profile(username):
    vids = Video.query.filter_by(uploader=username).all()
    content = f"<h4>Profil de {username}</h4><div class='row mt-2'>"
    for v in vids:
        content += f"""
        <div class='col-sm-6 col-md-4 col-lg-3 mb-3'>
            <div class='card card-dark'>
                <img src='{v.thumbnail or "https://placehold.co/400x225"}' class='thumb'>
                <div class='p-2'>
                    <div class='video-title'>{v.title}</div>
                    <div class='meta'>{v.category}</div>
                </div>
            </div>
        </div>
        """
    content += "</div>"
    return render_template_string(BASE_TEMPLATE, title=f"Profil {username}", content=content)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
