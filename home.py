from flask import Flask, render_template_string, request, jsonify
import random

app = Flask(__name__)

# Sample mock video data (no real adult content) - only placeholders and titles
CATEGORIES = ["Popular", "Amateur", "Pro", "VR", "ASMR", "Comedy"]
VIDEOS = [
    {
        "id": i,
        "title": f"Clip drôle #{i} - (mock)",
        "duration": f"{random.randint(1,12)}:{random.randint(0,59):02}",
        "views": random.randint(1_000, 5_000_000),
        "category": random.choice(CATEGORIES),
        # Picsum provides harmless placeholder images
        "thumb": f"https://picsum.photos/seed/{i}/400/225"
    }
    for i in range(1, 31)
]

INDEX_HTML = """
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MockHub — interface factice (pour blague)</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      body { background:#0f0f12; color:#e9ecef; }
      .brand { color: #ff6600; font-weight:700; font-size:1.6rem }
      .card { background:#141418; border:1px solid #222 }
      .thumb { height:140px; object-fit:cover; width:100% }
      .tag { background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:12px }
      .search-input { background:#0b0b0d; color:#eee; border:1px solid #222 }
    </style>
  </head>
  <body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark px-3">
      <a class="navbar-brand brand" href="#">MockHub</a>
      <div class="collapse navbar-collapse">
        <ul class="navbar-nav me-auto">
          <li class="nav-item"><a class="nav-link" href="#">Accueil</a></li>
          <li class="nav-item"><a class="nav-link" href="#">Top</a></li>
          <li class="nav-item"><a class="nav-link" href="#">Chaînes</a></li>
        </ul>
        <form class="d-flex" role="search" onsubmit="return false;">
          <input id="q" class="form-control me-2 search-input" type="search" placeholder="Rechercher (mock)" aria-label="Search">
          <button id="searchBtn" class="btn btn-outline-light" type="button">Rechercher</button>
        </form>
      </div>
    </nav>

    <div class="container-fluid mt-3">
      <div class="row">
        <div class="col-md-2 d-none d-md-block">
          <div class="card p-3 mb-3">
            <h6>Catégories</h6>
            <div id="cats">
              {% for c in categories %}
                <button class="btn btn-sm btn-outline-secondary mb-1 w-100 cat-btn" data-cat="{{c}}">{{c}}</button>
              {% endfor %}
              <button class="btn btn-sm btn-outline-secondary mb-1 w-100" id="clear-cat">Toutes</button>
            </div>
          </div>
          <div class="card p-3">
            <h6>Filtrer</h6>
            <div class="form-check">
              <input class="form-check-input" type="checkbox" value="popular" id="popOnly">
              <label class="form-check-label" for="popOnly">Que les plus vus</label>
            </div>
          </div>
        </div>

        <div class="col-md-10">
          <div class="mb-3">
            <h3>En vedette</h3>
            <div class="row" id="videos">
              {% for v in videos %}
                <div class="col-sm-6 col-md-4 col-lg-3 mb-3 video-card" data-title="{{v.title | lower}}" data-cat="{{v.category}}" data-views="{{v.views}}">
                  <div class="card h-100">
                    <img src="{{v.thumb}}" class="thumb card-img-top" alt="thumb">
                    <div class="card-body p-2">
                      <h6 class="card-title mb-1">{{v.title}}</h6>
                      <p class="mb-1"><span class="tag">{{v.category}}</span> • {{v.duration}} • {{v.views}} vues</p>
                      <button class="btn btn-sm btn-outline-light play-btn" data-id="{{v.id}}">Lire</button>
                    </div>
                  </div>
                </div>
              {% endfor %}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <div class="modal fade" id="playerModal" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content bg-dark text-light">
          <div class="modal-header border-0">
            <h5 class="modal-title" id="playerTitle">Lecture (mock)</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div id="playerPlaceholder" style="height:420px; background:#000; display:flex; align-items:center; justify-content:center; color:#bbb;">
              Contenu simulé — pas de contenu réel.
            </div>
          </div>
        </div>
      </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
      const videos = Array.from(document.querySelectorAll('.video-card'));
      const modal = new bootstrap.Modal(document.getElementById('playerModal'));

      document.getElementById('searchBtn').addEventListener('click', applyFilter);
      document.getElementById('q').addEventListener('keyup', (e) => { if(e.key==='Enter') applyFilter(); });
      document.querySelectorAll('.cat-btn').forEach(b=>b.addEventListener('click', ()=>{ setCategory(b.dataset.cat); }));
      document.getElementById('clear-cat').addEventListener('click', ()=>{ setCategory(''); });

      document.querySelectorAll('.play-btn').forEach(b => {
        b.addEventListener('click', (e)=>{
          const id = b.dataset.id;
          const card = b.closest('.video-card');
          document.getElementById('playerTitle').textContent = card.querySelector('.card-title').textContent;
          modal.show();
        });
      });

      function setCategory(cat) {
        document.querySelectorAll('.cat-btn').forEach(x=>x.classList.remove('active'));
        if(!cat) {
          videos.forEach(v=>v.style.display='block');
          return;
        }
        document.querySelectorAll(`.cat-btn[data-cat='${cat}']`)[0]?.classList.add('active');
        videos.forEach(v=> v.dataset.cat===cat ? v.style.display='block' : v.style.display='none');
      }

      function applyFilter() {
        const q = document.getElementById('q').value.trim().toLowerCase();
        const popOnly = document.getElementById('popOnly').checked;
        videos.forEach(v=>{
          const title = v.dataset.title;
          const views = parseInt(v.dataset.views,10);
          let show = true;
          if(q && !title.includes(q)) show = false;
          if(popOnly && views < 100_000) show = false;
          v.style.display = show ? 'block' : 'none';
        });
      }
    </script>
  </body>
</html>
"""

@app.route('/')
def index():
    q = request.args.get('q','')
    return render_template_string(INDEX_HTML, videos=VIDEOS, categories=CATEGORIES)

if __name__ == '__main__':
    app.run(debug=True)
