from flask import Flask, request, jsonify, send_from_directory, session, Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import sqlite3, os, secrets, json

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "database.sqlite")
STATIC_DIR = os.path.join(APP_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
app.secret_key = os.environ.get("APP_SECRET_KEY", secrets.token_hex(32))

ELECTION_DATA = {
  "mayors": [
    "David Bongiovanni",
    "Nicola Barbera",
    "Melangela Scolaro"
  ],
  "lists": {
    "Città Aperta - Controcorrente": {
      "coalition": "David Bongiovanni",
      "candidates": [
        "Ben R'Houma Monia",
        "Campo Raffaella",
        "Centineo Pietro",
        "Chiofalo Gaetano",
        "Cicero Antonino",
        "Crinò Pietro",
        "Gattignolo Elisa",
        "Giglio Antonio Mario",
        "Maio Antonino",
        "Mamì Antonio Dario",
        "Materia Claudio",
        "Mirabile Katia",
        "Naselli Domenica Adele detta Mimma",
        "Paratore Sebastiano Giuseppe Marco",
        "Poma Elena Albertina",
        "Puliafito Salvatore Giovanni",
        "Putzu Giovanna",
        "Rivilli Noelia Jacqueline",
        "Salerni Angelo",
        "Sidoti Gabriele",
        "Siracusa Carmela",
        "Torre Giovanna",
        "Valenti Maria Carmen",
        "Yahiaoui Ayoub"
      ]
    },
    "Movimento 2050": {
      "coalition": "David Bongiovanni",
      "candidates": [
        "Arrigo Antonino",
        "Cambria Angelino detto Linuccio",
        "Ciminelli Erika",
        "Coppolino Maria Pia",
        "Corrado Fabrizio",
        "Donnina Giovanni",
        "El Hessania Abdelkrim detto Karim",
        "Genovese Biagio",
        "Giglio Ruggero detto Ruggero",
        "Giorgianni Vera detta Vera",
        "Giunta Antonino",
        "Giunta Gabriella",
        "Infantino Marco",
        "Mazzeo Angelo",
        "Mirabile Alessandra Rosaria",
        "Presti Stefania",
        "Recupero Gaetano",
        "Turrisi Giuseppe detto Gepi"
      ]
    },
    "Partito Democratico": {
      "coalition": "David Bongiovanni",
      "candidates": [
        "Bongiovanni David",
        "Calamuneri Orazio",
        "Ceraolo Carmelo Michele",
        "Cucumo Stefania",
        "Di Pasquale Francesco detto Franco",
        "Epifanio Stefania",
        "Floramo Domenica detta Dominga",
        "Franchina Loredana",
        "Garofalo Mario",
        "Gitto Lorenzo",
        "Imbesi Gianluca",
        "Immesi Ilenia detta Ilenia",
        "Lembo Giusy detta Giusi",
        "Mancuso Felice",
        "Mostaccio Domenica",
        "Nichitellea Nicoleta Mariana detta Nicoletta",
        "Saija Stefano Antonio",
        "Santanocita Francesca",
        "Spinella Paolo",
        "Torre Rosaria detta Sara",
        "Tujiri Khadija detta Gigia",
        "Turrisi Antonio",
        "Vazza Milena",
        "Zangla Angela"
      ]
    },
    "De Luca Sindaco di Sicilia": {
      "coalition": "Melangela Scolaro",
      "candidates": [
        "Dominga Accetta",
        "Sebastiano Borghese",
        "Angela Maria Calatozzo",
        "Claudia Cappellano",
        "Pranvera Cecaj",
        "Giuseppe Crisafulli",
        "Luca Cucinotta",
        "Nunziata Graziella D’Amico detta D’Amico Nancy",
        "Claudio Febo",
        "Simona Gitto",
        "Vanessa Lo Monaco",
        "Francesca Lucia Mandanici detta Francesca Mandanici",
        "Clarissa Marcini",
        "Annalisa Munafò",
        "Celestina Nania",
        "Paolo Pino",
        "Giuseppe Puliafito detto Rubens",
        "Federico Scarpaci",
        "Sergio Vito Scolaro detto Sergio Scolaro",
        "Giulia Maria Sidoti detta Giulia",
        "Fabiana Simonetta",
        "Antonio Sofia",
        "Rita Spiccia",
        "Nicola Torre"
      ]
    },
    "Avremo Cura di Te": {
      "coalition": "Melangela Scolaro",
      "candidates": [
        "Graziano Angelo Accetta detto Graziano",
        "Mariadriana Aloisi",
        "Cristian Bambaci",
        "Gian Franco Brigandì",
        "Emanuela Bucca",
        "Carmelo Bucca",
        "Santa Caliri",
        "Salvatore Callisto",
        "Barbara Cavallaro",
        "Serena Maria Consoli",
        "Sebastiano Corica",
        "Vincenzo Foti",
        "Giuseppe Isgrò",
        "Giuseppe Laquidara detto Giuseppe Laguidara detto Giuseppe La Guidara",
        "Emanuele Munafò",
        "Rosario Carmelo Natale detto Rosario Natale",
        "Valentina Giusy Pantè",
        "Maurizio Pizzuto",
        "Gisella Puddu",
        "Gabriele Spina"
      ]
    },
    "Scolaro Sindaco": {
      "coalition": "Melangela Scolaro",
      "candidates": [
        "Nievis Maria Accetta detta Nives Accetta",
        "Concetta Alosi detta Cetty Alosi",
        "Anastasi Marco detto Marco Nastasi",
        "Fortunato Barbaro",
        "Sara Assunta Agostina Basilicò detta Sara Basilicò",
        "Giovanni Benenati",
        "Vincenza Brigandì",
        "Filippo Castellano",
        "Orazio Cicciari",
        "Tindaro Di Pasquale",
        "Costanza Gallo",
        "Luana Carmen Maccari detta Luana Maccari",
        "Alessia Merlino",
        "Alessandro Nania",
        "Salvatore Presti",
        "Carmelita Previti",
        "Salvatore Puliafito",
        "Giovanna Stefania Punturo detta Giovanna",
        "Simona Clementina Rosina detta Simona Rosina",
        "Sandy Siracusa detta Sendy Siracusa",
        "Rosalba Cinzia Smedile detta Cinzia Smedile",
        "Giuseppe Sottile",
        "Stefano Sturniolo",
        "Giovanni Valenti"
      ]
    },
    "Una Marcia in Più": {
      "coalition": "Melangela Scolaro",
      "candidates": [
        "Amalia Abbate",
        "Luca Arcoraci",
        "Carmelo Bilardo",
        "Antonino Biondo",
        "Cosimo Bucca",
        "Carmela Calabrese",
        "Lucia Caliri",
        "Antonino Composto",
        "Rosario Condipodero",
        "Vincenzo Crinò",
        "Mirko Fortunato De Pasquale",
        "Habderramin El Horche detto Abramo",
        "Elida Guray",
        "Zezem Ibtisem detta Sem",
        "Giovanna Lo Cascio",
        "Dario Angelo Maimone",
        "Roberta Maria Mancuso detta Roberta",
        "Salvatore Ragusa",
        "Ignazio Rotella",
        "Benedetto Russo",
        "Melangela Scolaro",
        "Antonino Sottile",
        "Guglielmo Torre",
        "Josè Angelo Virgillito detto Virgillito"
      ]
    },
    "Barcellona Pozzo di Gotto in Comune": {
      "coalition": "Melangela Scolaro",
      "candidates": [
        "Giuseppe Abbate",
        "Paolo Calabrò",
        "Carmelo Fabio Cappellano detto Fabio",
        "Leone Casile",
        "Walter Giuseppe Coppolino",
        "Giuseppe Crisafulli",
        "Gian Paolo Genovese",
        "Francesca Mariapia Giunta",
        "Francesco Giunta",
        "Santina Giunta",
        "Giuseppa Pasqua Grasso detta Giusy",
        "Antonino Lizio detto Anthony",
        "Alessandra Maio",
        "Giuseppe Mandanici",
        "Melania Antonella Mazzeo",
        "Gaetano Mercadante",
        "Cristina Miano",
        "Rosario Molica Franco",
        "Stefano Antonino Pellegrino",
        "Donato Raimondo",
        "Filippo Russo",
        "Maria Donatella Sottile",
        "Ilenia Torre",
        "Daniele Trovato"
      ]
    },
    "Fratelli d’Italia": {
      "coalition": "Nicola Barbera",
      "candidates": [
        "Eduardo Barca detto Eduardo",
        "Giorgio Leonardo Catalfamo",
        "Salvatore Chillemi",
        "Vera Cucé",
        "Fortunato D’Amico",
        "Luigi Sebastiano Dalia",
        "Erika De Francesco",
        "Greta Di Nuzzo detta Dinuzzo",
        "Carmelo Giunta",
        "Carmela Imbesi detta Carmen detta Guercio",
        "Vanessa Christine Isgrò",
        "Giampiero La Rosa detto Larosa",
        "Antonina Lepro detta Antonella",
        "Francesca Tindara Lo Presti",
        "Alessandra Mirabile",
        "Cesare Molino",
        "Daisy Francesca Munnia",
        "Anna Muscarà",
        "Angelo Paride Pino detto Paride detto Angelo",
        "Agostina Recupero",
        "Aurora Stincone",
        "Concetta Saporita",
        "Maria Gabriela Torre",
        "Evelyn Tindara Trapani"
      ]
    },
    "Nicola Barbera Sindaco": {
      "coalition": "Nicola Barbera",
      "candidates": [
        "Sebastiano Bauro",
        "Michele Bengala",
        "Giovanni Battista Bucalo detto Titta detto Bucolo",
        "Tiziano Chiofalo",
        "Cettina Cicciari",
        "Maria Cicero",
        "Domenico Giunta",
        "Maria Granata",
        "Francesco Fazio",
        "Giulia Floramo",
        "Chiara Italiano",
        "Tindara Labozzetta detta Tina",
        "Sonia Lanza",
        "Lucia Mazzeo",
        "Patrizia Antonella Milone",
        "Lorenzo Munafò",
        "Giuseppe Occello",
        "Francesco Perdichizzi",
        "Carmelo Pirri",
        "Daniela Porcino",
        "Carmelo Ravidà",
        "Antonino Stefano Sottile",
        "Andreana Francesca Speciale",
        "Irene Stagno"
      ]
    },
    "La Civica Barcellona P.G.": {
      "coalition": "Nicola Barbera",
      "candidates": [
        "Sandra Alesci",
        "Carmen Alesci",
        "Maria Carmela Buccheri",
        "Cosimo Calvo",
        "Pamela Campo",
        "Antonella Capone",
        "Vincenzo Catanesi",
        "Maria Chillemi",
        "Antonina Rosalia Smeralda Costantino",
        "Irene Fazio",
        "Giorgio Ferrara",
        "Gianluca Angelo Grasso",
        "Cosimo Glielmi",
        "Giuseppina Liotta",
        "Martina Maio",
        "Carmelo Munafò",
        "Caterina Puliafito",
        "Angela Salmeri",
        "Luciano Samuele Scarpaci",
        "Maria Scolaro",
        "Velio Andrea Spartà",
        "Salvatore Trasacco",
        "Michele Letterio Zangla",
        "Carmelina Zarcone"
      ]
    },
    "Fuori dal Coro": {
      "coalition": "Nicola Barbera",
      "candidates": [
        "Roberto Molino",
        "Michele Mandanici",
        "Antonino Tindaro Mangano detto Nino",
        "Laura Antonella Aliberti",
        "Rosa Salvo",
        "Francesca Caliri",
        "Filippa Simona Maggistro Contenta",
        "Wafaa Zanbib",
        "Corrada Siracusa",
        "Carmelo Viola",
        "Shpresa Senaj detta Speranza",
        "Caterina Agrillo detta Katrine",
        "Federico Di Salvo",
        "Lucia Gerbino detta Lucia Pulejo",
        "Sebastiana Calabrò detta Liliana",
        "Tindaro Grasso",
        "Giuseppina Sottile",
        "Caterina Bartolone",
        "Mauro Branciforte",
        "Andrea Giulio Giorgianni",
        "Eleonora Maria Ilacqua",
        "Maria Vanessa Sindoni",
        "Aurora Torre",
        "Rosalia Pagano"
      ]
    },
    "Ascoltiamo Barcellona": {
      "coalition": "Nicola Barbera",
      "candidates": [
        "Enrico Alfio Baccarini",
        "Vittoria Bertami",
        "Domenico Mirko Bonaceto",
        "Giuseppe Cambria",
        "Maria Conti",
        "Francesco Cordaro",
        "Caterina Chiofalo",
        "Provvidenza Antonina Chiofalo",
        "Maria Tindara Gullo",
        "Myriam Iuculano",
        "Nunzio La Macchia",
        "Giuseppe Lembo",
        "Domenica Milone",
        "Michele Pino",
        "Ludovica Raffa",
        "Natale Tindaro Paratore",
        "Claudio Pascalone",
        "Luca Talamo"
      ]
    },
    "Noi Ci Siamo": {
      "coalition": "Nicola Barbera",
      "candidates": [
        "Maria Carmela Abbate",
        "Giovanni Alesci",
        "Salvatore Benenati",
        "Ornella Tindara Cannata",
        "Giuseppe Catalano",
        "Vivianna Coppolino",
        "Doriana D’Amico",
        "Martin Elias Fazio",
        "Stefano Giorgianni",
        "Francesco Giunta",
        "Arleta Teresa Lis",
        "Giuseppe Maio",
        "Maria Grazia Mazzeo",
        "Sebastiano Salvatore Miano",
        "Vincenzo Nania",
        "Maria Otera",
        "Daniele Piccolo",
        "Clelia Puddu",
        "Daniela Saffioti",
        "Giuseppe Antonino Scarpaci",
        "Salvatore Torre",
        "Salvatore Trifilò",
        "Marco Viola"
      ]
    },
    "Forza Italia": {
      "coalition": "Nicola Barbera",
      "candidates": [
        "Alfredo Giovanni Aspa",
        "Luigi Bambaci",
        "Mario Barresi",
        "Orazio Beninati",
        "Antonio Biondo",
        "Paola Bucca",
        "Angela Bucolo",
        "Carmelo Calderone",
        "Maria Caruso",
        "Tindaro Giovinazzo",
        "Daniela Iannello",
        "Andreana Impollino detta Liliana",
        "Marika Lax detta Catalfamo",
        "Sebastiano Migliore",
        "Carmela Perdichizzi detta Carmelina",
        "Tommaso Maria Pino",
        "Lidia Pirri",
        "Francesco Puliafito",
        "Carmen Elena Rominu",
        "Daniela Scarpaci",
        "Jasmine Sciacca",
        "Gianluca Sidoti",
        "Elisabetta Sofia",
        "Domenico Trio detto Mimmo"
      ]
    },
    "Azzurri per Barcellona P.G.": {
      "coalition": "Nicola Barbera",
      "candidates": [
        "Alessandro Abbate",
        "Giuseppe Antonio Aliquò",
        "Fabiana Bartolotta detta Fabiana",
        "Gianfranco Benenati",
        "Giovanni Campanella",
        "Cosima Anna Caranna",
        "Franco Salvatore Caruso",
        "Giuseppe Coppolino",
        "Riccardo D’Amico",
        "Giovanni De Pasquale",
        "Antonella Drago Ferrante",
        "Graziella Genovese",
        "Lorenzo Gitto",
        "Caterina Vanessa Giunta",
        "Ferdinando Grosso",
        "Valeria Italiano",
        "Oksana Kravchenko detta Oxa",
        "Diego Lanza",
        "Luana Concetta Marchese",
        "Eleonora Maria Antonina Marzullo",
        "Sebastiano Mazzeo",
        "Alessandro Miano",
        "Yvonne Saja",
        "Antonino Sciacca"
      ]
    },
    "Vamos! Con Barbera Sindaco": {
      "coalition": "Nicola Barbera",
      "candidates": [
        "Giuseppe Giovanni Alosi detto Peppino",
        "Andrea Barresi",
        "Rosario Bilardo",
        "Maria Tindara Biondo",
        "Fulvio Luca Bucca",
        "Carmelo Calderone",
        "Santina Elvira Capone",
        "Nicolò Chillemi",
        "Antonino D’Amico",
        "Giusi D’Angelo",
        "Marisa Di Salvo",
        "Antonino Famà",
        "Rosario Ingegneri",
        "Francesco La Rocca detto Franco",
        "Pietro Marchese",
        "Angela Mendolia",
        "Elibjonda Metushaj detta Eli",
        "Maria Carmela Miano",
        "Carmelina Milone",
        "Paolo Piccolo",
        "Angela Telleri",
        "Rita Torre",
        "Denise Traviglia",
        "Carmela Villalba detta Carmen"
      ]
    }
  }
}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL UNIQUE,
        pin_hash TEXT NOT NULL,
        qr_token TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL,
        section TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        section TEXT NOT NULL,
                created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        vote_type TEXT NOT NULL,
        list_name TEXT,
        name TEXT NOT NULL,
        votes INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(report_id) REFERENCES reports(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    defaults = {
        "total_electors": "0",
        "total_voters": "0",
        "council_seats": "24",
        "winner_mayor": "David Bongiovanni",
        "mode": "first"
    }
    for k, v in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?,?)", (k, v))

    cur.execute("SELECT COUNT(*) AS n FROM users")
    if cur.fetchone()["n"] == 0:
        now = datetime.now().isoformat(timespec="seconds")
        demo = [
            ("Amministratore Centrale", "admin", "1234", "admin", None),
            ("Rappresentante Sezione 1", "3330000001", "1111", "rappresentante", "1"),
            ("Rappresentante Sezione 2", "3330000002", "2222", "rappresentante", "2")
        ]
        for name, phone, pin, role, section in demo:
            cur.execute(
                "INSERT INTO users(name, phone, pin_hash, qr_token, role, section, active, created_at) VALUES(?,?,?,?,?,?,1,?)",
                (name, phone, generate_password_hash(pin), secrets.token_urlsafe(24), role, section, now)
            )
    conn.commit()
    conn.close()

@app.before_request
def ensure_db():
    if not os.path.exists(DB_PATH):
        init_db()

def current_user():
    uid = session.get("uid")
    if not uid:
        return None
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=? AND active=1", (uid,)).fetchone()
    conn.close()
    return user

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({"ok": False, "error": "Accesso non autorizzato"}), 401
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"ok": False, "error": "Accesso non autorizzato"}), 401
        if user["role"] != "admin":
            return jsonify({"ok": False, "error": "Funzione riservata all'amministratore"}), 403
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/admin")
def admin_page():
    return send_from_directory(STATIC_DIR, "admin.html")

@app.post("/api/login")
def login():
    data = request.get_json(force=True)
    phone = str(data.get("phone", "")).strip()
    pin = str(data.get("pin", "")).strip()
    token = str(data.get("token", "")).strip()
    conn = db()
    user = None
    if token:
        user = conn.execute("SELECT * FROM users WHERE qr_token=? AND active=1", (token,)).fetchone()
    elif phone and pin:
        user = conn.execute("SELECT * FROM users WHERE phone=? AND active=1", (phone,)).fetchone()
        if user and not check_password_hash(user["pin_hash"], pin):
            user = None
    conn.close()
    if not user:
        return jsonify({"ok": False, "error": "Credenziali non valide"}), 401
    session["uid"] = user["id"]
    return jsonify({"ok": True, "user": dict_public_user(user)})

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

def dict_public_user(user):
    return {"name": user["name"], "phone": user["phone"], "role": user["role"], "section": user["section"]}

@app.get("/api/me")
@login_required
def me():
    return jsonify({"ok": True, "user": dict_public_user(current_user())})

@app.get("/api/config")
@login_required
def config():
    return jsonify({"ok": True, "data": ELECTION_DATA})

@app.post("/api/report")
@login_required
def save_report():
    user = current_user()
    data = request.get_json(force=True)
    section = str(data.get("section", "")).strip()
    mayors = data.get("mayors", {})
    list_votes = data.get("list_votes", {})
    preferences = data.get("preferences", {})
    if not section:
        return jsonify({"ok": False, "error": "Inserire la sezione"}), 400
    if user["role"] != "admin" and user["section"] and section != user["section"]:
        return jsonify({"ok": False, "error": "Rappresentante non autorizzato per questa sezione"}), 403

    now = datetime.now().isoformat(timespec="seconds")
    conn = db()
    cur = conn.cursor()
    existing = cur.execute("SELECT id FROM reports WHERE user_id=? AND section=?", (user["id"], section)).fetchone()
    if existing:
        report_id = existing["id"]
        cur.execute("UPDATE reports SET updated_at=? WHERE id=?", (now, report_id))
        cur.execute("DELETE FROM votes WHERE report_id=?", (report_id,))
    else:
        cur.execute("INSERT INTO reports(user_id, section, created_at, updated_at) VALUES(?,?,?,?)", (user["id"], section, now, now))
        report_id = cur.lastrowid

    for name in ELECTION_DATA["mayors"]:
        cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
                    (report_id, "sindaco", None, name, int(mayors.get(name, 0) or 0)))

    for list_name, obj in ELECTION_DATA["lists"].items():
        cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
                    (report_id, "lista", list_name, list_name, int(list_votes.get(list_name, 0) or 0)))
        pref_for_list = preferences.get(list_name, {})
        for cand in obj["candidates"]:
            cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
                        (report_id, "preferenza", list_name, cand, int(pref_for_list.get(cand, 0) or 0)))
    conn.commit()
    election = compute_elected(conn)
    conn.close()
    return jsonify({"ok": True, "message": "Dati inviati al server centrale"})


def get_settings(conn):
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    s = {r["key"]: r["value"] for r in rows}
    return {
        "total_electors": int(s.get("total_electors", "0") or 0),
        "total_voters": int(s.get("total_voters", "0") or 0),
        "council_seats": int(s.get("council_seats", "24") or 24),
        "winner_mayor": s.get("winner_mayor", "David Bongiovanni"),
        "mode": s.get("mode", "first")
    }

def d_hondt(votes, seats):
    result = {k: 0 for k in votes}
    quotients = []
    for k, v in votes.items():
        for d in range(1, seats + 1):
            quotients.append((v / d if d else 0, k, v, d))
    quotients.sort(key=lambda x: (-x[0], -x[2], x[1]))
    for _, k, _, _ in quotients[:seats]:
        result[k] += 1
    return result

def compute_elected(conn):
    settings = get_settings(conn)
    seats = max(1, int(settings["council_seats"]))
    winner = settings["winner_mayor"]
    mode = settings["mode"]

    mayor_rows = conn.execute("SELECT name, SUM(votes) AS total FROM votes WHERE vote_type='sindaco' GROUP BY name").fetchall()
    list_rows = conn.execute("SELECT list_name AS name, SUM(votes) AS total FROM votes WHERE vote_type='lista' GROUP BY list_name").fetchall()
    pref_rows = conn.execute("SELECT list_name, name, SUM(votes) AS total FROM votes WHERE vote_type='preferenza' GROUP BY list_name, name").fetchall()

    mayor_votes = {r["name"]: int(r["total"] or 0) for r in mayor_rows}
    list_votes = {r["name"]: int(r["total"] or 0) for r in list_rows}
    total_list_votes = sum(list_votes.values())

    threshold = total_list_votes * 0.05
    admitted_lists = {k: v for k, v in list_votes.items() if v > 0 and v >= threshold}

    coalition_votes = {}
    for lname, votes in admitted_lists.items():
        coalition = ELECTION_DATA["lists"][lname]["coalition"]
        coalition_votes[coalition] = coalition_votes.get(coalition, 0) + votes

    coalition_seats = d_hondt(coalition_votes, seats) if coalition_votes else {}

    winner_coal_votes = coalition_votes.get(winner, 0)
    winner_pct = (winner_coal_votes / total_list_votes * 100) if total_list_votes else 0
    other_max_pct = 0
    for c, v in coalition_votes.items():
        if c != winner and total_list_votes:
            other_max_pct = max(other_max_pct, v / total_list_votes * 100)

    import math
    premium_seats = math.ceil(seats * 0.60)
    natural_winner_seats = coalition_seats.get(winner, 0)
    premium_applied = (
        natural_winner_seats < premium_seats and
        other_max_pct <= 50 and
        (mode == "runoff" or winner_pct >= 40)
    )

    if premium_applied:
        coalition_seats[winner] = premium_seats
        remaining = seats - premium_seats
        others = {c: v for c, v in coalition_votes.items() if c != winner}
        other_seats = d_hondt(others, remaining) if others and remaining > 0 else {}
        for c in others:
            coalition_seats[c] = other_seats.get(c, 0)

    list_seats = {}
    for coalition, coalition_seat_count in coalition_seats.items():
        in_coalition = {l: v for l, v in admitted_lists.items() if ELECTION_DATA["lists"][l]["coalition"] == coalition}
        assigned = d_hondt(in_coalition, coalition_seat_count) if in_coalition and coalition_seat_count > 0 else {}
        list_seats.update(assigned)

    pref_map = {}
    for r in pref_rows:
        pref_map.setdefault(r["list_name"], {})[r["name"]] = int(r["total"] or 0)

    elected = {}
    for lname, obj in ELECTION_DATA["lists"].items():
        count = list_seats.get(lname, 0)
        ranked = []
        for idx, cand in enumerate(obj["candidates"]):
            ranked.append({"name": cand, "votes": pref_map.get(lname, {}).get(cand, 0), "order": idx + 1})
        ranked.sort(key=lambda x: (-x["votes"], x["order"]))
        elected[lname] = ranked[:count]

    losing_mayors = sorted(
        [{"name": m, "votes": mayor_votes.get(m, 0)} for m in ELECTION_DATA["mayors"] if m != winner],
        key=lambda x: -x["votes"]
    )

    return {
        "settings": settings,
        "mayor_votes": mayor_votes,
        "list_votes": list_votes,
        "total_list_votes": total_list_votes,
        "threshold": threshold,
        "admitted_lists": admitted_lists,
        "coalition_votes": coalition_votes,
        "coalition_seats": coalition_seats,
        "list_seats": list_seats,
        "elected": elected,
        "premium_applied": premium_applied,
        "premium_seats": premium_seats,
        "winner_pct": winner_pct,
        "other_max_pct": other_max_pct,
        "losing_mayors": losing_mayors
    }

@app.get("/api/dashboard")
@admin_required
def dashboard():
    conn = db()
    mayors = conn.execute("""
        SELECT name, SUM(votes) AS total FROM votes WHERE vote_type='sindaco'
        GROUP BY name ORDER BY total DESC
    """).fetchall()
    lists = conn.execute("""
        SELECT list_name AS name, SUM(votes) AS total FROM votes WHERE vote_type='lista'
        GROUP BY list_name ORDER BY total DESC
    """).fetchall()
    prefs = conn.execute("""
        SELECT list_name, name, SUM(votes) AS total FROM votes WHERE vote_type='preferenza'
        GROUP BY list_name, name ORDER BY total DESC
    """).fetchall()
    sections = conn.execute("""
        SELECT r.section, u.name AS representative, r.updated_at,
          SUM(CASE WHEN v.vote_type='sindaco' THEN v.votes ELSE 0 END) AS total_mayors,
          SUM(CASE WHEN v.vote_type='lista' THEN v.votes ELSE 0 END) AS total_lists,
          SUM(CASE WHEN v.vote_type='preferenza' THEN v.votes ELSE 0 END) AS total_preferences
        FROM reports r JOIN users u ON u.id=r.user_id JOIN votes v ON v.report_id=r.id
        GROUP BY r.id ORDER BY CAST(r.section AS INTEGER), r.section
    """).fetchall()
    election = compute_elected(conn)
    conn.close()
    return jsonify({
        "ok": True,
        "mayors": [dict(x) for x in mayors],
        "lists": [dict(x) for x in lists],
        "preferences": [dict(x) for x in prefs],
        "sections": [dict(x) for x in sections],
        "data": ELECTION_DATA,
        "election": election
    })

@app.get("/api/users")
@admin_required
def users():
    conn = db()
    rows = conn.execute("SELECT id, name, phone, role, section, qr_token, active FROM users ORDER BY id").fetchall()
    election = compute_elected(conn)
    conn.close()
    return jsonify({"ok": True, "users": [dict(r) for r in rows]})

@app.post("/api/users")
@admin_required
def create_user():
    data = request.get_json(force=True)
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    pin = str(data.get("pin", "")).strip()
    section = str(data.get("section", "")).strip() or None
    role = str(data.get("role", "rappresentante")).strip()
    if not name or not phone or not pin:
        return jsonify({"ok": False, "error": "Nome, telefono/codice e PIN sono obbligatori"}), 400
    conn = db()
    try:
        conn.execute("INSERT INTO users(name, phone, pin_hash, qr_token, role, section, active, created_at) VALUES(?,?,?,?,?,?,1,?)",
                     (name, phone, generate_password_hash(pin), secrets.token_urlsafe(24), role, section, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"ok": False, "error": "Telefono/codice già esistente"}), 409
    election = compute_elected(conn)
    conn.close()
    return jsonify({"ok": True})


@app.post("/api/settings")
@admin_required
def update_settings():
    data = request.get_json(force=True)
    allowed = ["total_electors", "total_voters", "council_seats", "winner_mayor", "mode"]
    conn = db()
    cur = conn.cursor()
    for k in allowed:
        if k in data:
            cur.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (k, str(data[k])))
    conn.commit()
    settings = get_settings(conn)
    conn.close()
    return jsonify({"ok": True, "settings": settings})

@app.post("/api/reset-votes")
@admin_required
def reset_votes():
    data = request.get_json(force=True)
    confirm = str(data.get("confirm", "")).strip()
    if confirm != "AZZERA":
        return jsonify({"ok": False, "error": "Conferma non valida. Scrivere AZZERA."}), 400
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM votes")
    cur.execute("DELETE FROM reports")
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "Voti azzerati"})

@app.delete("/api/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    user = current_user()
    if user["id"] == user_id:
        return jsonify({"ok": False, "error": "Non puoi rimuovere l'utente attualmente collegato"}), 400
    conn = db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.patch("/api/users/<int:user_id>/toggle")
@admin_required
def toggle_user(user_id):
    user = current_user()
    if user["id"] == user_id:
        return jsonify({"ok": False, "error": "Non puoi disattivare l'utente attualmente collegato"}), 400
    conn = db()
    row = conn.execute("SELECT active FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Utente non trovato"}), 404
    new_active = 0 if row["active"] else 1
    conn.execute("UPDATE users SET active=? WHERE id=?", (new_active, user_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "active": new_active})

@app.get("/api/export.csv")
@admin_required
def export_csv():
    conn = db()
    rows = conn.execute("""
        SELECT r.section, u.name AS representative, r.updated_at, v.vote_type, v.list_name, v.name, v.votes
        FROM reports r JOIN users u ON u.id=r.user_id JOIN votes v ON v.report_id=r.id
        ORDER BY r.section, v.vote_type, v.list_name, v.name
    """).fetchall()
    conn.close()
    lines = ["Sezione;Rappresentante;Aggiornato;Tipo;Lista;Nome;Voti"]
    for r in rows:
        lines.append(f"{r['section']};{r['representative']};{r['updated_at']};{r['vote_type']};{r['list_name'] or ''};{r['name']};{r['votes']}")
    return Response("\n".join(lines), mimetype="text/csv", headers={"Content-Disposition":"attachment; filename=report_comunali_barcellona.csv"})

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
