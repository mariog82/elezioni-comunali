import csv
import io

from flask import Flask, request, jsonify, send_from_directory, session, Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import sqlite3, os, secrets, math

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "database.sqlite")
STATIC_DIR = os.path.join(APP_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
app.secret_key = os.environ.get("APP_SECRET_KEY", secrets.token_hex(32))

ELECTION_DATA = {
  "mayors": [
    "Nicola Barbera",
    "David Bongiovanni",
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
    "Movimento 5Stelle": {
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
      "candidates": []
    },
    "Avremo Cura di Te": {
      "coalition": "Melangela Scolaro",
      "candidates": []
    },
    "Scolaro Sindaco": {
      "coalition": "Melangela Scolaro",
      "candidates": []
    },
    "Una Marcia in Più": {
      "coalition": "Melangela Scolaro",
      "candidates": []
    },
    "Barcellona Pozzo di Gotto in Comune": {
      "coalition": "Melangela Scolaro",
      "candidates": []
    },
    "Fratelli d’Italia": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Nicola Barbera Sindaco": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "La Civica Barcellona P.G.": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Fuori dal Coro": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Ascoltiamo Barcellona": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Noi Ci Siamo": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Forza Italia": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Azzurri per Barcellona P.G.": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Vamos! Con Barbera Sindaco": {
      "coalition": "Nicola Barbera",
      "candidates": []
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
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL UNIQUE,
        pin_hash TEXT NOT NULL,
        qr_token TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL,
        section TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        section TEXT NOT NULL,
        voters INTEGER NOT NULL DEFAULT 0,
        blank_ballots INTEGER NOT NULL DEFAULT 0,
        null_ballots INTEGER NOT NULL DEFAULT 0,
        contested_ballots INTEGER NOT NULL DEFAULT 0,
        closed INTEGER NOT NULL DEFAULT 0,
        closed_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id INTEGER NOT NULL,
        vote_type TEXT NOT NULL,
        list_name TEXT,
        name TEXT NOT NULL,
        votes INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(report_id) REFERENCES reports(id)
    )""")

    report_cols = [row["name"] for row in cur.execute("PRAGMA table_info(reports)").fetchall()]
    migrations = {
        "voters": "ALTER TABLE reports ADD COLUMN voters INTEGER NOT NULL DEFAULT 0",
        "blank_ballots": "ALTER TABLE reports ADD COLUMN blank_ballots INTEGER NOT NULL DEFAULT 0",
        "null_ballots": "ALTER TABLE reports ADD COLUMN null_ballots INTEGER NOT NULL DEFAULT 0",
        "contested_ballots": "ALTER TABLE reports ADD COLUMN contested_ballots INTEGER NOT NULL DEFAULT 0",
        "closed": "ALTER TABLE reports ADD COLUMN closed INTEGER NOT NULL DEFAULT 0",
        "closed_at": "ALTER TABLE reports ADD COLUMN closed_at TEXT"
    }
    for col, sql in migrations.items():
        if col not in report_cols:
            cur.execute(sql)

    cur.execute("""CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )""")
    defaults = {
        "total_electors": "0",
        "total_voters": "0",
        "council_seats": "24",
        "winner_mayor": "David Bongiovanni",
        "mode": "first"
    }
    for key, value in defaults.items():
        cur.execute("INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)", (key, value))
    cur.execute("SELECT COUNT(*) AS n FROM users")
    if cur.fetchone()["n"] == 0:
        now = datetime.now().isoformat(timespec="seconds")
        demo_users = [
            ("Amministratore Centrale", "admin", "1234", "admin", None),
            ("Rappresentante Sezione 1", "3330000001", "1111", "rappresentante", "1"),
            ("Rappresentante Sezione 2", "3330000002", "2222", "rappresentante", "2"),
        ]
        for name, phone, pin, role, section in demo_users:
            cur.execute(
                "INSERT INTO users(name, phone, pin_hash, qr_token, role, section, active, created_at) VALUES(?,?,?,?,?,?,1,?)",
                (name, phone, generate_password_hash(pin), secrets.token_urlsafe(24), role, section, now),
            )
    conn.commit()
    conn.close()

@app.before_request
def ensure_db():
    if not os.path.exists(DB_PATH):
        init_db()

def current_user():
    user_id = session.get("uid")
    if not user_id:
        return None
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=? AND active=1", (user_id,)).fetchone()
    conn.close()
    return user

def public_user(user):
    return {"id": user["id"], "name": user["name"], "phone": user["phone"], "role": user["role"], "section": user["section"]}

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

def get_settings(conn):
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    settings = {r["key"]: r["value"] for r in rows}
    return {
        "total_electors": int(settings.get("total_electors", "0") or 0),
        "total_voters": int(settings.get("total_voters", "0") or 0),
        "council_seats": int(settings.get("council_seats", "24") or 24),
        "winner_mayor": settings.get("winner_mayor", "David Bongiovanni"),
        "mode": settings.get("mode", "first"),
    }

def d_hondt(votes, seats):
    result = {key: 0 for key in votes}
    quotients = []
    for key, value in votes.items():
        for divisor in range(1, seats + 1):
            quotients.append((value / divisor if divisor else 0, key, value, divisor))
    quotients.sort(key=lambda item: (-item[0], -item[2], item[1]))
    for _, key, _, _ in quotients[:seats]:
        result[key] += 1
    return result

def compute_elected(conn):
    settings = get_settings(conn)
    seats = max(1, settings["council_seats"])
    winner = settings["winner_mayor"]
    mode = settings["mode"]
    list_rows = conn.execute("SELECT list_name AS name, SUM(votes) AS total FROM votes WHERE vote_type='lista' GROUP BY list_name").fetchall()
    pref_rows = conn.execute("SELECT list_name, name, SUM(votes) AS total FROM votes WHERE vote_type='preferenza' GROUP BY list_name, name").fetchall()
    mayor_rows = conn.execute("SELECT name, SUM(votes) AS total FROM votes WHERE vote_type='sindaco' GROUP BY name").fetchall()
    mayor_votes = {row["name"]: int(row["total"] or 0) for row in mayor_rows}
    list_votes = {row["name"]: int(row["total"] or 0) for row in list_rows}
    total_list_votes = sum(list_votes.values())
    threshold = total_list_votes * 0.05
    admitted_lists = {name: votes for name, votes in list_votes.items() if votes > 0 and votes >= threshold}
    coalition_votes = {}
    for list_name, votes in admitted_lists.items():
        coalition = ELECTION_DATA["lists"][list_name]["coalition"]
        coalition_votes[coalition] = coalition_votes.get(coalition, 0) + votes
    coalition_seats = d_hondt(coalition_votes, seats) if coalition_votes else {}
    winner_coal_votes = coalition_votes.get(winner, 0)
    winner_pct = (winner_coal_votes / total_list_votes * 100) if total_list_votes else 0
    other_max_pct = max([v / total_list_votes * 100 for c, v in coalition_votes.items() if c != winner] or [0]) if total_list_votes else 0
    premium_seats = math.ceil(seats * 0.60)
    natural_winner_seats = coalition_seats.get(winner, 0)
    premium_applied = natural_winner_seats < premium_seats and other_max_pct <= 50 and (mode == "runoff" or winner_pct >= 40)
    if premium_applied:
        coalition_seats[winner] = premium_seats
        remaining_seats = seats - premium_seats
        other_coalitions = {coalition: votes for coalition, votes in coalition_votes.items() if coalition != winner}
        other_seats = d_hondt(other_coalitions, remaining_seats) if other_coalitions and remaining_seats > 0 else {}
        for coalition in other_coalitions:
            coalition_seats[coalition] = other_seats.get(coalition, 0)
    list_seats = {}
    for coalition, coalition_seat_count in coalition_seats.items():
        lists_in_coalition = {list_name: votes for list_name, votes in admitted_lists.items() if ELECTION_DATA["lists"][list_name]["coalition"] == coalition}
        assigned = d_hondt(lists_in_coalition, coalition_seat_count) if lists_in_coalition and coalition_seat_count > 0 else {}
        list_seats.update(assigned)
    preferences = {}
    for row in pref_rows:
        preferences.setdefault(row["list_name"], {})[row["name"]] = int(row["total"] or 0)
    elected = {}
    for list_name, list_obj in ELECTION_DATA["lists"].items():
        count = list_seats.get(list_name, 0)
        ranked = []
        for index, candidate in enumerate(list_obj["candidates"]):
            ranked.append({"name": candidate, "votes": preferences.get(list_name, {}).get(candidate, 0), "order": index + 1})
        ranked.sort(key=lambda item: (-item["votes"], item["order"]))
        elected[list_name] = ranked[:count]
    losing_mayors = sorted([{"name": name, "votes": mayor_votes.get(name, 0)} for name in ELECTION_DATA["mayors"] if name != winner], key=lambda item: -item["votes"])
    return {
        "settings": settings, "mayor_votes": mayor_votes, "list_votes": list_votes,
        "total_list_votes": total_list_votes, "threshold": threshold,
        "admitted_lists": admitted_lists, "coalition_votes": coalition_votes,
        "coalition_seats": coalition_seats, "list_seats": list_seats,
        "elected": elected, "premium_applied": premium_applied,
        "premium_seats": premium_seats, "winner_pct": winner_pct,
        "other_max_pct": other_max_pct, "losing_mayors": losing_mayors,
    }

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
    return jsonify({"ok": True, "user": public_user(user)})

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.get("/api/me")
@login_required
def me():
    return jsonify({"ok": True, "user": public_user(current_user())})

@app.get("/api/config")
@login_required
def config():
    conn = db()
    settings = get_settings(conn)
    conn.close()
    return jsonify({"ok": True, "data": ELECTION_DATA, "settings": settings})


@app.get("/api/my-report")
@login_required
def my_report():
    user = current_user()
    section = request.args.get("section", user["section"] or "").strip()

    if not section:
        return jsonify({"ok": True, "exists": False})

    if user["role"] != "admin" and user["section"] and section != user["section"]:
        return jsonify({"ok": False, "error": "Rappresentante non autorizzato per questa sezione"}), 403

    conn = db()
    report = conn.execute(
        "SELECT * FROM reports WHERE section=? ORDER BY updated_at DESC LIMIT 1",
        (section,)
    ).fetchone()

    if not report:
        conn.close()
        return jsonify({"ok": True, "exists": False, "section": section})

    votes = conn.execute(
        "SELECT vote_type, list_name, name, votes FROM votes WHERE report_id=?",
        (report["id"],)
    ).fetchall()
    conn.close()

    mayors = {}
    list_votes = {}
    preferences = {}

    for row in votes:
        if row["vote_type"] == "sindaco":
            mayors[row["name"]] = row["votes"]
        elif row["vote_type"] == "lista":
            list_votes[row["list_name"]] = row["votes"]
        elif row["vote_type"] == "preferenza":
            preferences.setdefault(row["list_name"], {})
            preferences[row["list_name"]][row["name"]] = row["votes"]

    return jsonify({
        "ok": True,
        "exists": True,
        "section": report["section"],
        "voters": report["voters"],
        "blank_ballots": report["blank_ballots"],
        "null_ballots": report["null_ballots"],
        "contested_ballots": report["contested_ballots"],
        "closed": bool(report["closed"]),
        "closed_at": report["closed_at"],
        "mayors": mayors,
        "list_votes": list_votes,
        "preferences": preferences,
        "updated_at": report["updated_at"]
    })

@app.post("/api/report")
@login_required
def save_report():
    user = current_user()
    data = request.get_json(force=True)
    section = str(data.get("section", "")).strip()
    voters = int(data.get("voters", 0) or 0)
    blank_ballots = int(data.get("blank_ballots", 0) or 0)
    null_ballots = int(data.get("null_ballots", 0) or 0)
    contested_ballots = int(data.get("contested_ballots", 0) or 0)
    mayor_votes = data.get("mayors", {})
    list_votes = data.get("list_votes", {})
    preferences = data.get("preferences", {})
    if not section:
        return jsonify({"ok": False, "error": "Inserire la sezione"}), 400
    if user["role"] != "admin" and user["section"] and section != user["section"]:
        return jsonify({"ok": False, "error": "Rappresentante non autorizzato per questa sezione"}), 403
    valid_mayor_votes = sum(int(v or 0) for v in mayor_votes.values())
    valid_list_votes = sum(int(v or 0) for v in list_votes.values())
    valid_votes = max(valid_mayor_votes, valid_list_votes)
    expected_voters = valid_votes + blank_ballots + null_ballots
    # Invio parziale consentito anche se la quadratura non è definitiva.
    # Il controllo bloccante avviene solo con il pulsante Chiudi seggio.
    now = datetime.now().isoformat(timespec="seconds")
    conn = db()
    cur = conn.cursor()
    existing = cur.execute("SELECT id, closed FROM reports WHERE user_id=? AND section=?", (user["id"], section)).fetchone()
    if existing and user["role"] != "admin" and existing["closed"]:
        conn.close()
        return jsonify({"ok": False, "error": "Il seggio risulta già chiuso. Non puoi più modificare o inviare dati."}), 403
    if existing:
        report_id = existing["id"]
        cur.execute("UPDATE reports SET voters=?, blank_ballots=?, null_ballots=?, contested_ballots=?, updated_at=? WHERE id=?", (voters, blank_ballots, null_ballots, contested_ballots, now, report_id))
        cur.execute("DELETE FROM votes WHERE report_id=?", (report_id,))
    else:
        cur.execute("INSERT INTO reports(user_id, section, voters, blank_ballots, null_ballots, contested_ballots, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)", (user["id"], section, voters, blank_ballots, null_ballots, contested_ballots, now, now))
        report_id = cur.lastrowid
    for name in ELECTION_DATA["mayors"]:
        cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "sindaco", None, name, int(mayor_votes.get(name, 0) or 0)))
    for list_name, list_obj in ELECTION_DATA["lists"].items():
        cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "lista", list_name, list_name, int(list_votes.get(list_name, 0) or 0)))
        pref_for_list = preferences.get(list_name, {})
        for candidate in list_obj["candidates"]:
            cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "preferenza", list_name, candidate, int(pref_for_list.get(candidate, 0) or 0)))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "Dati inviati al server centrale"})


@app.get("/api/section-status")
@login_required
def section_status():
    user = current_user()
    section = request.args.get("section", user["section"] or "").strip()
    if not section:
        return jsonify({"ok": True, "closed": False, "section": section})
    conn = db()
    row = conn.execute("SELECT closed, closed_at FROM reports WHERE section=? ORDER BY updated_at DESC LIMIT 1", (section,)).fetchone()
    conn.close()
    return jsonify({"ok": True, "section": section, "closed": bool(row["closed"]) if row else False, "closed_at": row["closed_at"] if row else None})

@app.post("/api/close-seat")
@login_required
def close_seat():
    user = current_user()
    if user["role"] == "admin":
        return jsonify({"ok": False, "error": "La chiusura seggio è riservata al rappresentante."}), 403
    data = request.get_json(force=True)
    section = str(data.get("section", "")).strip()
    voters = int(data.get("voters", 0) or 0)
    blank_ballots = int(data.get("blank_ballots", 0) or 0)
    null_ballots = int(data.get("null_ballots", 0) or 0)
    contested_ballots = int(data.get("contested_ballots", 0) or 0)
    mayor_votes = data.get("mayors", {})
    list_votes = data.get("list_votes", {})
    preferences = data.get("preferences", {})
    if not section:
        return jsonify({"ok": False, "error": "Inserire la sezione"}), 400
    if user["section"] and section != user["section"]:
        return jsonify({"ok": False, "error": "Rappresentante non autorizzato per questa sezione"}), 403
    valid_mayor_votes = sum(int(v or 0) for v in mayor_votes.values())
    valid_list_votes = sum(int(v or 0) for v in list_votes.values())
    valid_votes = max(valid_mayor_votes, valid_list_votes)
    expected_voters = valid_votes + blank_ballots + null_ballots
    if voters != expected_voters:
        return jsonify({"ok": False, "error": f"Non è possibile chiudere il seggio: votanti={voters}, totale valido + bianche + nulle={expected_voters}. Le contestate sono solo indicative."}), 400
    now = datetime.now().isoformat(timespec="seconds")
    conn = db(); cur = conn.cursor()
    existing = cur.execute("SELECT id, closed FROM reports WHERE user_id=? AND section=?", (user["id"], section)).fetchone()
    if existing and existing["closed"]:
        conn.close(); return jsonify({"ok": False, "error": "Il seggio è già chiuso."}), 403
    if existing:
        report_id = existing["id"]
        cur.execute("UPDATE reports SET voters=?, blank_ballots=?, null_ballots=?, contested_ballots=?, closed=1, closed_at=?, updated_at=? WHERE id=?", (voters, blank_ballots, null_ballots, contested_ballots, now, now, report_id))
        cur.execute("DELETE FROM votes WHERE report_id=?", (report_id,))
    else:
        cur.execute("INSERT INTO reports(user_id, section, voters, blank_ballots, null_ballots, contested_ballots, closed, closed_at, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (user["id"], section, voters, blank_ballots, null_ballots, contested_ballots, 1, now, now, now))
        report_id = cur.lastrowid
    for name in ELECTION_DATA["mayors"]:
        cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "sindaco", None, name, int(mayor_votes.get(name, 0) or 0)))
    for list_name, list_obj in ELECTION_DATA["lists"].items():
        cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "lista", list_name, list_name, int(list_votes.get(list_name, 0) or 0)))
        pref_for_list = preferences.get(list_name, {})
        for candidate in list_obj["candidates"]:
            cur.execute("INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)", (report_id, "preferenza", list_name, candidate, int(pref_for_list.get(candidate, 0) or 0)))
    conn.commit(); conn.close(); session.clear()
    return jsonify({"ok": True, "message": "Grazie per il tuo contributo. Il seggio è stato chiuso correttamente."})

@app.post("/api/reopen-section")
@admin_required
def reopen_section():
    data = request.get_json(force=True)
    section = str(data.get("section", "")).strip()
    if not section:
        return jsonify({"ok": False, "error": "Sezione obbligatoria"}), 400
    conn = db(); conn.execute("UPDATE reports SET closed=0, closed_at=NULL WHERE section=?", (section,)); conn.commit(); conn.close()
    return jsonify({"ok": True, "message": "Seggio riaperto"})

@app.get("/api/dashboard")
@admin_required
def dashboard():
    conn = db()
    mayors = conn.execute("SELECT name, SUM(votes) AS total FROM votes WHERE vote_type='sindaco' GROUP BY name ORDER BY total DESC").fetchall()
    lists = conn.execute("SELECT list_name AS name, SUM(votes) AS total FROM votes WHERE vote_type='lista' GROUP BY list_name ORDER BY total DESC").fetchall()
    preferences = conn.execute("SELECT list_name, name, SUM(votes) AS total FROM votes WHERE vote_type='preferenza' GROUP BY list_name, name ORDER BY total DESC").fetchall()
    sections = conn.execute("""
        SELECT r.section, u.name AS representative, r.updated_at,
          r.voters, r.blank_ballots, r.null_ballots, r.contested_ballots, r.closed, r.closed_at,
          SUM(CASE WHEN v.vote_type='sindaco' THEN v.votes ELSE 0 END) AS total_mayors,
          SUM(CASE WHEN v.vote_type='lista' THEN v.votes ELSE 0 END) AS total_lists,
          SUM(CASE WHEN v.vote_type='preferenza' THEN v.votes ELSE 0 END) AS total_preferences
        FROM reports r
        JOIN users u ON u.id=r.user_id
        JOIN votes v ON v.report_id=r.id
        GROUP BY r.id
        ORDER BY CAST(r.section AS INTEGER), r.section
    """).fetchall()
    ballot_totals = conn.execute("SELECT COALESCE(SUM(voters),0) AS voters, COALESCE(SUM(blank_ballots),0) AS blank_ballots, COALESCE(SUM(null_ballots),0) AS null_ballots, COALESCE(SUM(contested_ballots),0) AS contested_ballots FROM reports").fetchone()
    election = compute_elected(conn)
    conn.close()
    return jsonify({"ok": True, "mayors": [dict(row) for row in mayors], "lists": [dict(row) for row in lists], "preferences": [dict(row) for row in preferences], "sections": [dict(row) for row in sections], "ballot_totals": dict(ballot_totals), "data": ELECTION_DATA, "election": election})

@app.post("/api/settings")
@admin_required
def update_settings():
    data = request.get_json(force=True)
    allowed = ["total_electors", "total_voters", "council_seats", "winner_mayor", "mode"]
    conn = db()
    cur = conn.cursor()
    for key in allowed:
        if key in data:
            cur.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, str(data[key])))
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

@app.get("/api/users")
@admin_required
def users():
    conn = db()
    rows = conn.execute("SELECT id, name, phone, role, section, qr_token, active FROM users ORDER BY id").fetchall()
    conn.close()
    return jsonify({"ok": True, "users": [dict(row) for row in rows]})

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
        conn.execute("INSERT INTO users(name, phone, pin_hash, qr_token, role, section, active, created_at) VALUES(?,?,?,?,?,?,1,?)", (name, phone, generate_password_hash(pin), secrets.token_urlsafe(24), role, section, datetime.now().isoformat(timespec="seconds")))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"ok": False, "error": "Telefono/codice già esistente"}), 409
    conn.close()
    return jsonify({"ok": True})

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


@app.get("/api/section-details")
@admin_required
def section_details():
    conn = db()
    rows = conn.execute("""
        SELECT r.section, v.vote_type, v.list_name, v.name, v.votes
        FROM reports r
        JOIN votes v ON v.report_id = r.id
        ORDER BY CAST(r.section AS INTEGER), r.section, v.vote_type, v.list_name, v.name
    """).fetchall()
    conn.close()

    result = {}
    for row in rows:
        section = row["section"]
        if section not in result:
            result[section] = {
                "lists": {},
                "mayors": {},
                "preferences": {}
            }

        vote_type = row["vote_type"]
        if vote_type == "lista":
            result[section]["lists"][row["name"]] = row["votes"]
        elif vote_type == "sindaco":
            result[section]["mayors"][row["name"]] = row["votes"]
        elif vote_type == "preferenza":
            list_name = row["list_name"] or ""
            result[section]["preferences"].setdefault(list_name, {})
            result[section]["preferences"][list_name][row["name"]] = row["votes"]

    return jsonify({"ok": True, "sections": result, "data": ELECTION_DATA})

@app.get("/api/export.csv")
@admin_required
def export_csv():
    conn = db()

    # Migrazione di sicurezza nel caso il database SQLite esistente sia stato creato con una versione precedente.
    cur = conn.cursor()
    report_cols = [row["name"] for row in cur.execute("PRAGMA table_info(reports)").fetchall()]
    migrations = {
        "voters": "ALTER TABLE reports ADD COLUMN voters INTEGER NOT NULL DEFAULT 0",
        "blank_ballots": "ALTER TABLE reports ADD COLUMN blank_ballots INTEGER NOT NULL DEFAULT 0",
        "null_ballots": "ALTER TABLE reports ADD COLUMN null_ballots INTEGER NOT NULL DEFAULT 0",
        "contested_ballots": "ALTER TABLE reports ADD COLUMN contested_ballots INTEGER NOT NULL DEFAULT 0",
        "closed": "ALTER TABLE reports ADD COLUMN closed INTEGER NOT NULL DEFAULT 0",
        "closed_at": "ALTER TABLE reports ADD COLUMN closed_at TEXT"
    }
    for col, sql in migrations.items():
        if col not in report_cols:
            cur.execute(sql)
    conn.commit()

    rows = conn.execute("""
        SELECT
            r.section AS section,
            u.name AS representative,
            COALESCE(r.voters, 0) AS voters,
            COALESCE(r.blank_ballots, 0) AS blank_ballots,
            COALESCE(r.null_ballots, 0) AS null_ballots,
            COALESCE(r.contested_ballots, 0) AS contested_ballots,
            COALESCE(r.updated_at, '') AS updated_at,
            v.vote_type AS vote_type,
            COALESCE(v.list_name, '') AS list_name,
            v.name AS name,
            COALESCE(v.votes, 0) AS votes
        FROM reports r
        JOIN users u ON u.id = r.user_id
        JOIN votes v ON v.report_id = r.id
        ORDER BY r.section, v.vote_type, v.list_name, v.name
    """).fetchall()
    conn.close()

    output = io.StringIO()
    output.write("sep=;\n")

    writer = csv.writer(
        output,
        delimiter=";",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )

    writer.writerow([
        "Sezione",
        "Rappresentante",
        "Votanti",
        "Bianche",
        "Nulle",
        "Contestate",
        "Aggiornato",
        "Tipo",
        "Lista",
        "Nome",
        "Voti",
    ])

    for row in rows:
        writer.writerow([
            row["section"],
            row["representative"],
            row["voters"],
            row["blank_ballots"],
            row["null_ballots"],
            row["contested_ballots"],
            row["updated_at"],
            row["vote_type"],
            row["list_name"],
            row["name"],
            row["votes"],
        ])

    csv_content = "\ufeff" + output.getvalue()

    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=report_comunali_barcellona.csv"},
    )

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
