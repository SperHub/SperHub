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

import os
import sqlite3
import uuid
import subprocess
from datetime import datetime
from pathlib import Path
from functools import wraps

from flask import (Flask, render_template_string, request, redirect, url_for,
                   send_from_directory, flash, session, abort, Markup)

from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

# ---------- CONFIG ----------
BASE = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE / "uploads"
THUMB_DIR = BASE / "thumbnails"
DB_PATH = BASE / "friendhub.db"
ALLOWED = {"mp4", "webm", "mkv", "mov", "ogg"}
MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB max, adjust as needed
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-friendhub-secret")

for d in (UPLOAD_DIR, THUMB_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = SECRET_KEY

# ---------- DB UTIL ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """)
        db.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            title TEXT,
            filename TEXT,
            uploader TEXT,
            category TEXT,
            description TEXT,
            thumb_local INTEGER DEFAULT 0,
            created_at TEXT,
            views INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0
        )
        """)
        db.commit()

init_db()

# ---------- HELPERS ----------
def allowed_file(fname):
    return "." in fname and fname.rsplit(".", 1)[1].lower() in ALLOWED

def login_required(f):
    @wraps(f)
    def decorated(*a, **kw):
        if 'user' not in session:
            flash("Connecte-toi d'abord.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*a, **kw)
    return decorated

def try_extract_thumbnail(video_path: Path, out_path: Path):
    """
    Try to use ffmpeg to extract a frame at 3s to out_path.
    Returns True on success, False otherwise.
    """
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-ss", "00:00:03.000", "-vframes", "1",
            str(out_path)
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        return out_path.exists()
    except Exception:
        return False

# ---------- ROUTES ----------
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
  {% block content %}{% endblock %}
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

# INDEX
@app.route("/")
def index():
    q = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("category") or "").strip()
    with get_db() as db:
        if q and category:
            rows = db.execute("SELECT * FROM videos WHERE (lower(title) LIKE ? OR lower(description) LIKE ?) AND category=? ORDER BY created_at DESC",
                              (f"%{q}%", f"%{q}%", category)).fetchall()
        elif q:
            rows = db.execute("SELECT * FROM videos WHERE (lower(title) LIKE ? OR lower(description) LIKE ?) ORDER BY created_at DESC",
                              (f"%{q}%", f"%{q}%")).fetchall()
        elif category:
            rows = db.execute("SELECT * FROM videos WHERE category=? ORDER BY created_at DESC", (category,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
        videos = [dict(r) for r in rows]
    return render_template_string(BASE_TEMPLATE + """
    {% block content %}
    <h4>Vidéos populaires</h4>
    <div class="row mt-2">
      {% for v in videos %}
        <div class="col-6 col-md-3 mb-4">
          <div class="card card-dark h-100">
            <a href="{{ url_for('video_page', video_id=v['id']) }}">
              {% if v['thumb_local'] %}
                <img src="{{ url_for('thumb', filename=v['id'] + '.jpg') }}" class="thumb card-img-top" alt="">
              {% else %}
                <img src="https://picsum.photos/seed/{{ v['id'] }}/400/225" class="thumb card-img-top" alt="">
              {% endif %}
            </a>
            <div class="card-body p-2">
              <a href="{{ url_for('video_page', video_id=v['id']) }}" class="video-title">{{ v['title'] or 'Untitled' }}</a>
              <div class="meta">{{ v['uploader'] or 'anonyme' }} • {{ v['created_at'].split('T')[0] }} • {{ v['views'] }} vues</div>
              <div class="mt-2 d-flex justify-content-between align-items-center">
                <div class="category-badge">{{ v['category'] or 'Général' }}</div>
                <a class="btn btn-sm btn-outline-light" href="{{ url_for('video_page', video_id=v['id']) }}">Lire</a>
              </div>
            </div>
          </div>
        </div>
      {% endfor %}
      {% if not videos %}
        <div class="col-12"><div class="alert alert-info">Aucune vidéo pour l'instant — sois le premier à uploader !</div></div>
      {% endif %}
    </div>
    {% endblock %}
    """, videos=videos)

# UPLOAD
@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        title = request.form.get("title", "Untitled").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "Général").strip()
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Aucun fichier sélectionné.", "warning")
            return redirect(request.url)
        if not allowed_file(file.filename):
            flash("Format non supporté. Extensions autorisées: " + ", ".join(sorted(ALLOWED)), "warning")
            return redirect(request.url)
        original = secure_filename(file.filename)
        vid_id = str(uuid.uuid4())
        save_name = f"{vid_id}_{original}"
        save_path = UPLOAD_DIR / save_name
        file.save(save_path)
        # Try to generate thumbnail via ffmpeg
        thumb_path = THUMB_DIR / f"{vid_id}.jpg"
        got_thumb = try_extract_thumbnail(save_path, thumb_path)
        with get_db() as db:
            db.execute("INSERT INTO videos (id,title,filename,uploader,category,description,thumb_local,created_at) VALUES (?,?,?,?,?,?,?,?)",
                       (vid_id, title, save_name, session.get('user'), category, description, 1 if got_thumb else 0, datetime.utcnow().isoformat()))
            db.commit()
        flash(Markup("Upload reçu — vidéo disponible immédiatement si navigateur supporte le format. Tu peux partager la page vidéo : <b>/video/%s</b>" % vid_id), "success")
        return redirect(url_for('video_page', video_id=vid_id))
    return render_template_string(BASE_TEMPLATE + """
    {% block content %}
    <h4>Uploader une vidéo</h4>
    <div class="row">
      <div class="col-md-8">
        <form method="post" enctype="multipart/form-data">
          <div class="mb-3"><label class="form-label">Titre</label><input class="form-control" name="title" required></div>
          <div class="mb-3"><label class="form-label">Description</label><textarea class="form-control" name="description"></textarea></div>
          <div class="mb-3">
            <label class="form-label">Catégorie</label>
            <select name="category" class="form-select">
              <option>Funny</option><option>Gameplay</option><option>Vlog</option><option>Music</option><option>Prank</option>
            </select>
          </div>
          <div class="mb-3">
            <label class="form-label">Fichier vidéo</label>
            <input class="form-control" type="file" name="file" accept="video/*" required>
          </div>
          <button class="btn btn-accent" type="submit">Uploader</button>
        </form>
      </div>
      <div class="col-md-4">
        <h6>Conseils</h6>
        <ul>
          <li>Formats recommandés: MP4 / WebM</li>
          <li>Taille max: dépend de ta config (ici ~2GB)</li>
          <li>Si ffmpeg est installé, une miniature sera générée automatiquement.</li>
        </ul>
      </div>
    </div>
    {% endblock %}
    """)

# VIDEO PAGE
@app.route("/video/<video_id>")
def video_page(video_id):
    with get_db() as db:
        row = db.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()
        if not row:
            abort(404)
        v = dict(row)
        # increment views
        db.execute("UPDATE videos SET views = views + 1 WHERE id=?", (video_id,))
        db.commit()
    # decide video file path and thumbnail
    video_url = url_for('uploaded_file', filename=v['filename'])
    thumb_url = url_for('thumb', filename=v['id'] + '.jpg') if v['thumb_local'] else f"https://picsum.photos/seed/{v['id']}/800/450"
    return render_template_string(BASE_TEMPLATE + """
    {% block content %}
    <div class="row">
      <div class="col-md-8">
        <h3>{{ v['title'] }}</h3>
        <div class="small-muted mb-2">par <strong>{{ v['uploader'] }}</strong> • {{ v['created_at'].split('T')[0] }} • {{ v['views'] }} vues</div>
        <div class="card card-dark p-2">
          <video id="player" controls style="width:100%; max-height:70vh;" poster="{{ thumb_url }}">
            <source src="{{ video_url }}" type="video/mp4">
            Votre navigateur ne supporte pas la balise vidéo.
          </video>
        </div>

        <div class="mt-3">
          <strong>Description</strong>
          <p class="small-muted">{{ v['description'] or '—' }}</p>
        </div>
      </div>

      <div class="col-md-4">
        <div class="card card-dark p-3 mb-3">
          <h6>À propos</h6>
          <p class="small-muted">Catégorie: <span class="category-badge">{{ v['category'] }}</span></p>
          <p class="small-muted">Likes: {{ v['likes'] }} • ID: {{ v['id'] }}</p>
          {% if session.get('user') == v['uploader'] %}
            <div class="mt-2"><a class="btn btn-sm btn-outline-light" href="{{ url_for('delete_video', video_id=v['id']) }}" onclick="return confirm('Supprimer cette vidéo ?')">Supprimer</a></div>
          {% endif %}
        </div>

        <div class="card card-dark p-3">
          <h6>Uploader</h6>
          <p class="small-muted"><a href="{{ url_for('profile', username=v['uploader']) }}">{{ v['uploader'] }}</a></p>
          <hr style="border-color:var(--border)">
          <h6>Partager</h6>
          <input class="form-control" readonly value="{{ request.url }}">
        </div>
      </div>
    </div>
    {% endblock %}
    """, v=v, video_url=video_url, thumb_url=thumb_url)

# SERVE UPLOADS + THUMBS
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename, conditional=True)

@app.route("/thumbnails/<path:filename>")
def thumb(filename):
    return send_from_directory(THUMB_DIR, filename, conditional=True)

# REGISTER / LOGIN / LOGOUT
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        if not username or not password:
            flash("Nom d'utilisateur et mot de passe requis.", "warning")
            return redirect(request.url)
        phash = generate_password_hash(password)
        try:
            with get_db() as db:
                db.execute("INSERT INTO users (username,password_hash,created_at) VALUES (?,?,?)",
                           (username, phash, datetime.utcnow().isoformat()))
                db.commit()
            flash("Inscription réussie — connecte-toi.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Ce nom d'utilisateur est déjà pris.", "warning")
            return redirect(request.url)
    return render_template_string(BASE_TEMPLATE + """
    {% block content %}
    <div class="row">
      <div class="col-md-6">
        <h4>Inscription</h4>
        <form method="post">
          <div class="mb-3"><label>Nom d'utilisateur</label><input class="form-control" name="username" required></div>
          <div class="mb-3"><label>Mot de passe</label><input type="password" class="form-control" name="password" required></div>
          <button class="btn btn-accent" type="submit">S'inscrire</button>
        </form>
      </div>
    </div>
    {% endblock %}
    """)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        with get_db() as db:
            row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
            if row and check_password_hash(row["password_hash"], password):
                session['user'] = username
                flash("Connexion réussie.", "success")
                nxt = request.args.get('next') or url_for('index')
                return redirect(nxt)
            else:
                flash("Identifiants invalides.", "warning")
                return redirect(request.url)
    return render_template_string(BASE_TEMPLATE + """
    {% block content %}
    <div class="row">
      <div class="col-md-6">
        <h4>Se connecter</h4>
        <form method="post">
          <div class="mb-3"><label>Nom d'utilisateur</label><input class="form-control" name="username" required></div>
          <div class="mb-3"><label>Mot de passe</label><input type="password" class="form-control" name="password" required></div>
          <button class="btn btn-accent" type="submit">Se connecter</button>
        </form>
      </div>
    </div>
    {% endblock %}
    """)

@app.route("/logout")
def logout():
    session.pop('user', None)
    flash("Déconnecté.", "success")
    return redirect(url_for('index'))

# PROFILE
@app.route("/profile/<username>")
def profile(username):
    with get_db() as db:
        vids = db.execute("SELECT * FROM videos WHERE uploader=? ORDER BY created_at DESC", (username,)).fetchall()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        abort(404)
    return render_template_string(BASE_TEMPLATE + """
    {% block content %}
    <div class="row">
      <div class="col-md-3">
        <div class="card card-dark p-3">
          <h5>{{ username }}</h5>
          <p class="small-muted">Membre depuis {{ user['created_at'].split('T')[0] }}</p>
          {% if session.get('user') == username %}
            <a class="btn btn-sm btn-outline-light" href="{{ url_for('upload') }}">Uploader</a>
          {% endif %}
        </div>
      </div>
      <div class="col-md-9">
        <h5>Vidéos de {{ username }}</h5>
        <div class="row">
          {% for v in vids %}
            <div class="col-6 col-md-4 mb-3">
              <div class="card card-dark">
                <a href="{{ url_for('video_page', video_id=v['id']) }}">
                {% if v['thumb_local'] %}
                  <img src="{{ url_for('thumb', filename=v['id'] + '.jpg') }}" class="thumb card-img-top">
                {% else %}
                  <img src="https://picsum.photos/seed/{{ v['id'] }}/400/225" class="thumb card-img-top">
                {% endif %}
                </a>
                <div class="card-body p-2">
                  <a href="{{ url_for('video_page', video_id=v['id']) }}" class="video-title">{{ v['title'] }}</a>
                </div>
              </div>
            </div>
          {% endfor %}
          {% if not vids %}
            <div class="col-12"><div class="alert alert-info">Aucune vidéo publiée.</div></div>
          {% endif %}
        </div>
      </div>
    </div>
    {% endblock %}
    """, username=username, vids=[dict(r) for r in vids], user=dict(user))

# DELETE video (uploader only)
@app.route("/delete/<video_id>", methods=["GET"])
@login_required
def delete_video(video_id):
    with get_db() as db:
        row = db.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()
        if not row:
            abort(404)
        if row['uploader'] != session.get('user'):
            abort(403)
        # remove files
        try:
            fpath = UPLOAD_DIR / row['filename']
            if fpath.exists():
                fpath.unlink()
            tpath = THUMB_DIR / f"{video_id}.jpg"
            if tpath.exists():
                tpath.unlink()
        except Exception:
            pass
        db.execute("DELETE FROM videos WHERE id=?", (video_id,))
        db.commit()
    flash("Vidéo supprimée.", "success")
    return redirect(url_for('profile', username=session.get('user')))

# Simple admin endpoint to seed demo content
@app.route("/_seed_demo")
def seed_demo():
    # only allow if DB empty
    with get_db() as db:
        c = db.execute("SELECT COUNT(*) as c FROM videos").fetchone()["c"]
        if c > 0:
            flash("La DB contient déjà des vidéos.", "warning")
            return redirect(url_for('index'))
        # create demo user
        try:
            db.execute("INSERT INTO users (username,password_hash,created_at) VALUES (?,?,?)",
                       ("demo", generate_password_hash("demo"), datetime.utcnow().isoformat()))
        except Exception:
            pass
        # add demo entries (placeholders using picsum)
        import random
        cats = ["Funny","Gameplay","Vlog","Music","Prank"]
        for i in range(8):
            vid = str(uuid.uuid4())
            db.execute("INSERT INTO videos (id,title,filename,uploader,category,description,thumb_local,created_at,views,likes) VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (vid, f"Vidéo Demo #{i+1}", "", "demo", random.choice(cats),
                        "Contenu factice pour demo — pas de contenu explicite.", 0, datetime.utcnow().isoformat(), random.randint(0,5000), random.randint(0,500)))
        db.commit()
    flash("Données demo insérées. Utilisateur demo/demo", "success")
    return redirect(url_for('index'))

# ------------- RUN -------------
if __name__ == "__main__":
    print("FriendHub mock starting. Open http://127.0.0.1:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)

