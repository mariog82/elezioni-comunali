import unicodedata
import csv
import re
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
    "NICOLA BARBERA",
    "DAVID BONGIOVANNI",
    "MELANGELA SCOLARO"
  ],
  "lists": {}
}

def fast_pin_hash(pin):
    # Import CSV: hashing volutamente leggero per evitare timeout su Render.
    # check_password_hash resta compatibile con questo formato Werkzeug.
    return generate_password_hash(str(pin), method="pbkdf2:sha256:1", salt_length=4)

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
        "winner_mayor": "NICOLA BARBERA",
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

    # Un solo record logico per sezione/seggio:
    # primo inserimento = INSERT, salvataggi successivi = UPDATE.
    cur.execute("""
        DELETE FROM reports
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM reports
            GROUP BY section
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_section_unique ON reports(section)")


    # Deduplica voti storici: conserva l'ultimo record per report/tipo/lista/nome.
    cur.execute("""
        DELETE FROM votes
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM votes
            GROUP BY report_id, vote_type, COALESCE(list_name,''), name
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_votes_unique_update_import ON votes(report_id, vote_type, COALESCE(list_name,''), name)")


    # Deduplica report storici: un solo report per sezione/TOTALE.
    cur.execute("""
        DELETE FROM reports
        WHERE id NOT IN (
            SELECT MAX(id)
            FROM reports
            GROUP BY section
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_section_update_import ON reports(section)")


    # Deduplica voti importati: un solo record per report/tipo/lista/nome.
    cur.execute("""
        DELETE FROM votes
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM votes
            GROUP BY report_id, vote_type, COALESCE(list_name,''), name
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_votes_update_csv_unique_v56 ON votes(report_id, vote_type, COALESCE(list_name,''), name)")


    # UPDATE CSV: un solo report per sezione/TOTALE.
    cur.execute("""
        DELETE FROM reports
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM reports
            GROUP BY section
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_update_csv_v65 ON reports(section)")

    # UPDATE CSV: un solo voto per report/tipo/lista/nome.
    cur.execute("""
        DELETE FROM votes
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM votes
            GROUP BY report_id, vote_type, COALESCE(list_name,''), name
        )
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_votes_update_csv_v65 ON votes(report_id, vote_type, COALESCE(list_name,''), name)")

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
        "winner_mayor": settings.get("winner_mayor", "NICOLA BARBERA"),
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


@app.route("/admin/charts")
def admin_charts_page():
    return send_from_directory(STATIC_DIR, "admin_charts.html")

@app.route("/admin/imports")
def admin_imports_page():
    return send_from_directory(STATIC_DIR, "admin_imports.html")

@app.route("/admin/users")
def admin_users_page():
    return send_from_directory(STATIC_DIR, "admin_users.html")


@app.route("/admin/tools")
def admin_tools_page():
    return send_from_directory(STATIC_DIR, "admin_tools.html")

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
        "SELECT vote_type, list_name, name, name AS display_name, votes FROM votes WHERE report_id=?",
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
        "section_electors": report["contested_ballots"],
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
    section_electors = int(data.get("section_electors", data.get("contested_ballots", 0)) or 0)
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
    existing = cur.execute("SELECT id, closed FROM reports WHERE section=?", (section,)).fetchone()
    if existing and user["role"] != "admin" and existing["closed"]:
        conn.close()
        return jsonify({"ok": False, "error": "Il seggio risulta gia' chiuso. Non puoi piu' modificare o inviare dati."}), 403
    if existing:
        report_id = existing["id"]
        cur.execute("UPDATE reports SET voters=?, blank_ballots=?, null_ballots=?, contested_ballots=?, updated_at=? WHERE id=?", (voters, blank_ballots, null_ballots, section_electors, now, report_id))
        cur.execute("DELETE FROM votes WHERE report_id=?", (report_id,))
    else:
        cur.execute("INSERT INTO reports(user_id, section, voters, blank_ballots, null_ballots, contested_ballots, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?)", (user["id"], section, voters, blank_ballots, null_ballots, section_electors, now, now))
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
    section_electors = int(data.get("section_electors", data.get("contested_ballots", 0)) or 0)
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
    existing = cur.execute("SELECT id, closed FROM reports WHERE section=?", (section,)).fetchone()
    if existing and existing["closed"]:
        conn.close(); return jsonify({"ok": False, "error": "Il seggio è gia' chiuso."}), 403
    if existing:
        report_id = existing["id"]
        cur.execute("UPDATE reports SET voters=?, blank_ballots=?, null_ballots=?, contested_ballots=?, closed=1, closed_at=?, updated_at=? WHERE id=?", (voters, blank_ballots, null_ballots, section_electors, now, now, report_id))
        cur.execute("DELETE FROM votes WHERE report_id=?", (report_id,))
    else:
        cur.execute("INSERT INTO reports(user_id, section, voters, blank_ballots, null_ballots, contested_ballots, closed, closed_at, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (user["id"], section, voters, blank_ballots, null_ballots, section_electors, 1, now, now, now))
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

    now = datetime.now().isoformat(timespec="seconds")

    conn = db()
    cur = conn.cursor()

    row = cur.execute(
        "SELECT id FROM reports WHERE section=? ORDER BY updated_at DESC LIMIT 1",
        (section,)
    ).fetchone()

    if not row:
        conn.close()
        return jsonify({"ok": False, "error": "Nessuna rilevazione trovata per questo seggio"}), 404

    # Riattiva il seggio mantenendo tutti i dati gia' aggiornati presenti nel database.
    cur.execute(
        "UPDATE reports SET closed=0, closed_at=NULL, updated_at=? WHERE section=?",
        (now, section)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "message": "Seggio riattivato con i dati aggiornati gia' presenti. Il rappresentante può nuovamente accedere e modificare."
    })



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
    ballot_totals = conn.execute("SELECT COALESCE(SUM(voters),0) AS voters, COALESCE(SUM(blank_ballots),0) AS blank_ballots, COALESCE(SUM(null_ballots),0) AS null_ballots, COALESCE(SUM(contested_ballots),0) AS section_electors FROM reports").fetchone()
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
        return jsonify({"ok": False, "error": "Telefono/codice gia' esistente"}), 409
    conn.close()
    return jsonify({"ok": True})









def _norm(value):
    value = str(value or "").strip().lower()
    value = value.replace("’", "'").replace("`", "'").replace("´", "'")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value

def _tokens(value):
    value = str(value or "").strip().lower()
    value = value.replace("’", "'").replace("`", "'").replace("´", "'")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    tokens = re.findall(r"[a-z0-9]+", value)
    stop = {"detto","detta","di","de","del","della","dei","degli","delle","il","la","lo","le","i","gli","un","una","e","ed","con","per","sindaco","sindaca","lista"}
    return [t for t in tokens if t not in stop and len(t) > 1]

def _contains_flexible(csv_value, app_value):
    ck = _norm(csv_value)
    ak = _norm(app_value)
    if not ck or not ak:
        return False
    if ck == ak or ck in ak or ak in ck:
        return True
    ct = _tokens(csv_value)
    at = _tokens(app_value)
    if not ct or not at:
        return False
    csv_in_app = all(any(c == a or c in a or a in c for a in at) for c in ct)
    app_in_csv = all(any(a == c or a in c or c in a for c in ct) for a in at)
    return csv_in_app or app_in_csv

def _list_alias(key):
    aliases = {
        "movimento2050": "movimento5stelle",
        "movimento5stelle": "movimento5stelle",
        "m5s": "movimento5stelle",
        "pd": "partitodemocratico",
        "partitodemocratico": "partitodemocratico",
        "cittaaperta": "cittaapertacontrocorrente",
        "cittaapertacontrocorrente": "cittaapertacontrocorrente"
    }
    return aliases.get(key, key)

def _resolve_list(raw_name, raw_number=None):
    # Match per Nome Lista: numero lista usato solo se nessun nome combacia.
    raw_key = _list_alias(_norm(raw_name))
    matches = []
    for name in ELECTION_DATA["lists"].keys():
        app_key = _list_alias(_norm(name))
        if app_key == raw_key:
            return name
        if _contains_flexible(raw_name, name):
            matches.append(name)
    if matches:
        if len(matches) == 1:
            return matches[0]
        raw_tokens = set(_tokens(raw_name))
        matches.sort(key=lambda n: len(raw_tokens & set(_tokens(n))), reverse=True)
        return matches[0]
    try:
        n = int(str(raw_number or "").strip())
        lists = list(ELECTION_DATA["lists"].keys())
        if 1 <= n <= len(lists):
            return lists[n-1]
    except Exception:
        pass
    return None

def _resolve_mayor(raw_name, raw_number=None):
    matches = [m for m in ELECTION_DATA["mayors"] if _contains_flexible(raw_name, m)]
    if matches:
        if len(matches) == 1:
            return matches[0]
        raw_tokens = set(_tokens(raw_name))
        matches.sort(key=lambda n: len(raw_tokens & set(_tokens(n))), reverse=True)
        return matches[0]
    try:
        n = int(str(raw_number or "").strip())
        mayors = ELECTION_DATA["mayors"]
        if 1 <= n <= len(mayors):
            return mayors[n-1]
    except Exception:
        pass
    return None

def _resolve_candidate(list_name, raw_name, raw_number=None):
    candidates = ELECTION_DATA["lists"].get(list_name, {}).get("candidates", [])
    if not candidates:
        return None

    matches = []
    for cand in candidates:
        try:
            if _contains_flexible(raw_name, cand):
                matches.append(cand)
        except Exception:
            pass

    if not matches:
        raw_tokens = set(_tokens(raw_name))
        for cand in candidates:
            cand_tokens = set(_tokens(cand))
            if not raw_tokens or not cand_tokens:
                continue
            common = raw_tokens & cand_tokens
            min_required = 1 if min(len(raw_tokens), len(cand_tokens)) <= 1 else 2
            if len(common) >= min_required:
                matches.append(cand)

    if matches:
        if len(matches) == 1:
            return matches[0]
        raw_tokens = set(_tokens(raw_name))
        def _score(cand):
            cand_tokens = set(_tokens(cand))
            common = raw_tokens & cand_tokens
            return (len(common), len(common) / max(len(raw_tokens), 1), -abs(len(cand_tokens) - len(raw_tokens)))
        matches.sort(key=_score, reverse=True)
        return matches[0]

    try:
        n = int(str(raw_number or "").strip())
        if 1 <= n <= len(candidates):
            return candidates[n - 1]
    except Exception:
        pass

    return None



def _list_label_with_coalition(list_name):
    obj = ELECTION_DATA.get("lists", {}).get(list_name, {})
    coalition = str(obj.get("coalition", "") or "").strip()
    if coalition:
        return f"{list_name} - {coalition}"
    return list_name

def _ensure_dynamic_list(list_name, coalition=""):
    """
    UPDATE-FIRST:
    crea la lista se manca, altrimenti aggiorna coalizione e mantiene la lista esistente.
    """
    list_name = str(list_name or "").strip()
    coalition = str(coalition or "").strip()

    if not list_name:
        return None

    existing = _resolve_list(list_name, None)

    if existing:
        if coalition:
            ELECTION_DATA["lists"][existing]["coalition"] = coalition
        return existing

    ELECTION_DATA["lists"][list_name] = {
        "coalition": coalition,
        "candidates": []
    }
    return list_name


def _ensure_dynamic_candidate(list_name, candidate_name):
    """
    UPDATE-FIRST:
    crea il candidato se manca, altrimenti mantiene quello esistente.
    """
    list_name = str(list_name or "").strip()
    candidate_name = str(candidate_name or "").strip()

    if not list_name or not candidate_name:
        return None

    if list_name not in ELECTION_DATA["lists"]:
        ELECTION_DATA["lists"][list_name] = {
            "coalition": "",
            "candidates": []
        }

    existing = _resolve_candidate(list_name, candidate_name, None)

    if existing:
        return existing

    ELECTION_DATA["lists"][list_name]["candidates"].append(candidate_name)
    return candidate_name

def _ensure_report(cur, section, user_id):
    """
    UPDATE-FIRST:
    per ogni sezione/TOTALE mantiene un solo report.
    Se il report esiste lo aggiorna, se non esiste lo crea.
    """
    now = datetime.now().isoformat(timespec="seconds")
    section = str(section or "").strip() or "TOTALE"

    row = cur.execute(
        "SELECT id FROM reports WHERE section=? ORDER BY id ASC LIMIT 1",
        (section,)
    ).fetchone()

    if row:
        cur.execute(
            "UPDATE reports SET user_id=?, updated_at=? WHERE id=?",
            (user_id, now, row["id"])
        )
        return row["id"]

    cur.execute(
        "INSERT INTO reports(user_id, section, voters, blank_ballots, null_ballots, contested_ballots, closed, closed_at, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (user_id, section, 0, 0, 0, 0, 0, None, now, now)
    )
    report_id = cur.lastrowid

    for mayor in ELECTION_DATA["mayors"]:
        _upsert_vote(cur, report_id, "sindaco", mayor, 0, None)

    for list_name, obj in ELECTION_DATA["lists"].items():
        _upsert_vote(cur, report_id, "lista", list_name, 0, list_name)
        for cand in obj.get("candidates", []):
            _upsert_vote(cur, report_id, "preferenza", cand, 0, list_name)

    return report_id

def _upsert_vote(cur, report_id, vote_type, name, votes, list_name=None):
    """
    UPDATE-FIRST:
    aggiorna il voto esistente per report/tipo/lista/nome.
    Inserisce solo se il record non esiste.
    Se trova duplicati storici, mantiene il primo record e cancella gli altri.
    """
    votes = int(votes or 0)

    rows = cur.execute(
        """
        SELECT id FROM votes
        WHERE report_id=?
          AND vote_type=?
          AND COALESCE(list_name,'')=COALESCE(?, '')
          AND name=?
        ORDER BY id ASC
        """,
        (report_id, vote_type, list_name, name)
    ).fetchall()

    if rows:
        keep_id = rows[0]["id"]
        cur.execute("UPDATE votes SET votes=? WHERE id=?", (votes, keep_id))

        for dup in rows[1:]:
            cur.execute("DELETE FROM votes WHERE id=?", (dup["id"],))

        return keep_id

    cur.execute(
        "INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
        (report_id, vote_type, list_name, name, votes)
    )
    return cur.lastrowid

def _intv(value, default=0):
    """
    Conversione robusta a intero:
    - gestisce None;
    - stringhe vuote;
    - virgole/punti/spazi;
    - ritorna default in caso di errore.
    """
    try:
        if value is None:
            return default

        text = str(value).strip()

        if not text:
            return default

        text = text.replace(".", "").replace(",", ".")

        return int(float(text))
    except Exception:
        return default


def _read_csv_file(max_rows=10000):
    """
    Lettura CSV standardizzata per tutti gli import.
    Separatore obbligatorio: ;
    """
    if "file" not in request.files:
        raise ValueError("File CSV mancante")

    uploaded = request.files["file"]

    raw = uploaded.read()

    if not raw:
        raise ValueError("File CSV vuoto")

    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("File troppo grande (max 5MB)")

    text = raw.decode("utf-8-sig", errors="ignore")

    reader = csv.reader(io.StringIO(text), delimiter=";")

    rows = []

    for row in reader:
        cleaned = [str(x).strip() for x in row]

        if any(cleaned):
            rows.append(cleaned)

    if not rows:
        raise ValueError("CSV senza dati")

    if len(rows) > max_rows:
        raise ValueError(f"CSV troppo grande. Massimo {max_rows} righe")

    # Rimozione automatica intestazione
    first_line = ";".join(rows[0]).lower()

    header_keywords = [
        "sezione",
        "numero liste",
        "nome lista",
        "voti validi",
        "numero sind",
        "candidato sindaco",
        "numero cons",
        "nome cons",
        "schede nulle",
        "schede bianche"
    ]

    if any(k in first_line for k in header_keywords):
        rows = rows[1:]

    return rows


def _import_votes(kind, by_section):
    try:
        rows = _read_csv_file()
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": f"Errore lettura CSV: {str(exc)}"}), 400

    admin_user = current_user()
    if not admin_user:
        return jsonify({"ok": False, "error": "Utente amministratore non riconosciuto"}), 401

    conn = db()
    cur = conn.cursor()
    imported = 0
    skipped = 0
    errors = []
    # Per import preferenze totali/per sezione: accumula i voti dei consiglieri per lista
    # per aggiornare anche i voti della lista collegata.
    list_totals_from_preferences = {}

    try:
        # reset_all_candidates_import_done_v67
        # Solo per l'import CSV dei candidati totali (/api/import/consiglieri):
        # elimina liste/candidati/voti lista/preferenze esistenti e ricarica da zero.
        if kind == "consiglieri" and not by_section:
            cur.execute("DELETE FROM votes WHERE vote_type IN ('lista','preferenza')")
            ELECTION_DATA["lists"].clear()

        for idx, row in enumerate(rows, start=1):
            try:
                if not row or not any(str(x).strip() for x in row):
                    skipped += 1
                    continue

                section = "TOTALE"
                off = 0
                if by_section:
                    if len(row) < 1 or not str(row[0]).strip():
                        raise ValueError("sezione mancante")
                    section = str(row[0]).strip()
                    off = 1

                report_id = _ensure_report(cur, section, admin_user["id"])

                if kind == "liste":
                    if len(row) < off + 3:
                        raise ValueError("formato richiesto: [Sezione;]Numero Liste;Nome Lista;Voti validi")
                    nome_lista = str(row[off + 1]).strip()
                    list_name = _ensure_dynamic_list(nome_lista, "")
                    if not list_name:
                        raise ValueError(f"Nome Lista non trovato in app.py: {nome_lista}")
                    votes = _intv(row[off + 2])
                    _upsert_vote(cur, report_id, "lista", list_name, votes, list_name)
                    imported += 1

                elif kind == "sindaci":
                    if len(row) < off + 4:
                        raise ValueError("formato richiesto: [Sezione;]Numero Sind;Candidato Sindaco;Voti validi;Voti solo Sind")
                    nome_sindaco = str(row[off + 1]).strip()
                    mayor = _resolve_mayor(nome_sindaco, row[off])
                    if not mayor:
                        raise ValueError(f"Candidato Sindaco non trovato in app.py: {nome_sindaco}")
                    votes = _intv(row[off + 2])
                    only = _intv(row[off + 3])
                    _upsert_vote(cur, report_id, "sindaco", mayor, votes + only, None)
                    imported += 1

                elif kind == "consiglieri":
                    # Formato:
                    # [Sezione;]Numero Lista;Nome Lista;Coalizione;Numero Candidato;Nome Candidato
                    # Colonna Voti validi opzionale come ultima colonna.
                    if len(row) < off + 5:
                        raise ValueError("formato richiesto: [Sezione;]Numero Lista;Nome Lista;Coalizione;Numero Candidato;Nome Candidato")

                    numero_lista = row[off]
                    nome_lista = str(row[off + 1]).strip()
                    coalizione = str(row[off + 2]).strip()
                    numero_candidato = row[off + 3]
                    nome_candidato = str(row[off + 4]).strip()

                    list_name = _ensure_dynamic_list(nome_lista, coalizione)
                    if not list_name:
                        raise ValueError(f"Nome Lista non valido: {nome_lista}")

                    candidate = _ensure_dynamic_candidate(list_name, nome_candidato)
                    display_candidate_name = nome_candidato.strip()
                    if not candidate:
                        raise ValueError(f"Nome Candidato non valido per lista {list_name}: {nome_candidato}")

                    if len(row) > off + 5:
                        votes = _intv(row[off + 5])
                    else:
                        votes = 0

                    _upsert_vote(cur, report_id, "preferenza", candidate, votes, list_name)
                    list_totals_from_preferences[(report_id, list_name)] = list_totals_from_preferences.get((report_id, list_name), 0) + votes
                    imported += 1

                elif kind == "schede":
                    if len(row) < off + 4:
                        raise ValueError("formato richiesto: [Sezione;]Voti nulli;Schede nulle;Schede bianche;V.cont.NoAss.")
                    voti_nulli = _intv(row[off])
                    schede_nulle = _intv(row[off + 1])
                    schede_bianche = _intv(row[off + 2])
                    v_cont_no_ass = _intv(row[off + 3])
                    now = datetime.now().isoformat(timespec="seconds")
                    cur.execute(
                        "UPDATE reports SET null_ballots=?, blank_ballots=?, updated_at=? WHERE id=?",
                        (voti_nulli + schede_nulle + v_cont_no_ass, schede_bianche, now, report_id)
                    )
                    imported += 1

            except Exception as exc:
                skipped += 1
                if len(errors) < 50:
                    errors.append(f"Riga {idx}: {str(exc)}")

        # Se il file importato contiene preferenze consiglieri, aggiorna anche i voti
        # delle liste collegate. In questo modo i grafici liste/statistiche si aggiornano
        # automaticamente anche caricando solo il CSV delle preferenze.
        if kind == "consiglieri":
            for (report_id, list_name), total_votes in list_totals_from_preferences.items():
                _upsert_vote(cur, report_id, "lista", list_name, total_votes, list_name)

        conn.commit()

    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({"ok": False, "error": f"Errore import {kind}: {str(exc)}"}), 500

    conn.close()
    return jsonify({
        "ok": True,
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "message": f"Import completato. Righe assegnate {imported}, righe saltate {skipped}."
    })

@app.post("/api/import/liste")
@admin_required
def import_liste_totali():
    return _import_votes("liste", False)

@app.post("/api/import/liste-sezioni")
@admin_required
def import_liste_sezioni():
    return _import_votes("liste", True)

@app.post("/api/import/sindaci")
@admin_required
def import_sindaci_totali():
    return _import_votes("sindaci", False)

@app.post("/api/import/sindaci-sezioni")
@admin_required
def import_sindaci_sezioni():
    return _import_votes("sindaci", True)

@app.post("/api/import/consiglieri")
@admin_required
def import_consiglieri_totali():
    return _import_votes("consiglieri", False)

@app.post("/api/import/consiglieri-sezioni")
@admin_required
def import_consiglieri_sezioni():
    return _import_votes("consiglieri", True)

@app.post("/api/import/schede")
@admin_required
def import_schede_totali():
    return _import_votes("schede", False)

@app.post("/api/import/schede-sezioni")
@admin_required
def import_schede_sezioni():
    return _import_votes("schede", True)

@app.post("/api/sections/import-csv")
@admin_required
def import_sections_csv():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "File CSV mancante"}), 400

    uploaded_file = request.files["file"]

    try:
        raw = uploaded_file.read()
        if len(raw) > 512 * 1024:
            return jsonify({"ok": False, "error": "File troppo grande. Limite massimo: 512 KB"}), 400
        content = raw.decode("utf-8-sig", errors="ignore")
    except Exception:
        return jsonify({"ok": False, "error": "Impossibile leggere il file CSV"}), 400

    if not content.strip():
        return jsonify({"ok": False, "error": "CSV vuoto"}), 400

    reader = csv.reader(io.StringIO(content), delimiter=";")
    rows = []
    for row in reader:
        cleaned = [cell.strip() for cell in row]
        if any(cleaned):
            rows.append(cleaned)

    if not rows:
        return jsonify({"ok": False, "error": "CSV vuoto"}), 400

    first = ";".join(rows[0]).lower().replace(" ", "")
    if first.startswith("sezione;") or "elettori" in first or "votanti" in first:
        rows = rows[1:]

    imported = 0
    updated = 0
    skipped = 0
    errors = []
    now = datetime.now().isoformat(timespec="seconds")

    conn = db()
    cur = conn.cursor()
    admin_user = current_user()

    try:
        for idx, row in enumerate(rows, start=1):
            if len(row) < 3:
                skipped += 1
                errors.append(f"Riga {idx}: formato richiesto Sezione;Elettori;Votanti")
                continue

            section = row[0].strip()
            try:
                section_electors = int(str(row[1]).replace(".", "").replace(",", "").strip() or 0)
                voters = int(str(row[2]).replace(".", "").replace(",", "").strip() or 0)
            except ValueError:
                skipped += 1
                errors.append(f"Riga {idx}: elettori o votanti non numerici")
                continue

            if not section:
                skipped += 1
                errors.append(f"Riga {idx}: sezione mancante")
                continue

            existing = cur.execute("SELECT id, closed FROM reports WHERE section=?", (section,)).fetchone()

            if existing:
                # Aggiorna solo elettori e votanti, preservando bianche, nulle, voti e stato chiusura.
                cur.execute(
                    "UPDATE reports SET voters=?, contested_ballots=?, updated_at=? WHERE section=?",
                    (voters, section_electors, now, section)
                )
                updated += 1
            else:
                # Crea record base per la sezione. I voti saranno inseriti/aggiornati in seguito.
                cur.execute(
                    "INSERT INTO reports(user_id, section, voters, blank_ballots, null_ballots, contested_ballots, closed, closed_at, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (admin_user["id"], section, voters, 0, 0, section_electors, 0, None, now, now)
                )
                report_id = cur.lastrowid

                for name in ELECTION_DATA["mayors"]:
                    cur.execute(
                        "INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
                        (report_id, "sindaco", None, name, 0)
                    )

                for list_name, list_obj in ELECTION_DATA["lists"].items():
                    cur.execute(
                        "INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
                        (report_id, "lista", list_name, list_name, 0)
                    )

                    for candidate in list_obj["candidates"]:
                        cur.execute(
                            "INSERT INTO votes(report_id, vote_type, list_name, name, votes) VALUES(?,?,?,?,?)",
                            (report_id, "preferenza", list_name, candidate, 0)
                        )

                imported += 1

        conn.commit()

    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({"ok": False, "error": f"Errore import sezioni CSV: {str(exc)}"}), 500

    conn.close()

    return jsonify({
        "ok": True,
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:10],
        "message": f"Import sezioni completato. Create {imported}, aggiornate {updated}, saltate {skipped}."
    })

@app.post("/api/users/import-csv")
@admin_required
def import_users_csv():
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "File CSV mancante"}), 400

    uploaded_file = request.files["file"]

    try:
        raw = uploaded_file.read()
        if len(raw) > 256 * 1024:
            return jsonify({"ok": False, "error": "File troppo grande. Limite massimo: 256 KB"}), 400
        content = raw.decode("utf-8-sig", errors="ignore")
    except Exception:
        return jsonify({"ok": False, "error": "Impossibile leggere il file CSV"}), 400

    if not content.strip():
        return jsonify({"ok": False, "error": "CSV vuoto"}), 400

    reader = csv.reader(io.StringIO(content), delimiter=";")
    rows = []
    for row in reader:
        cleaned = [cell.strip() for cell in row]
        if any(cleaned):
            rows.append(cleaned)

    if not rows:
        return jsonify({"ok": False, "error": "CSV vuoto"}), 400

    first = ";".join(rows[0]).lower().replace(" ", "")
    if first.startswith("nome;") or "telefono" in first or "codice" in first:
        rows = rows[1:]

    # Batch piccolo per evitare timeout Gunicorn su Render free.
    if len(rows) > 100:
        return jsonify({
            "ok": False,
            "error": "Troppe righe. Import massimo consentito: 100 utenti per volta. Dividi il CSV in piu' file."
        }), 400

    now = datetime.now().isoformat(timespec="seconds")
    imported = 0
    updated = 0
    skipped = 0
    errors = []

    conn = db()
    cur = conn.cursor()

    try:
        existing_rows = cur.execute("SELECT phone FROM users").fetchall()
        existing_phones = {r["phone"] for r in existing_rows}

        # Cache hashing: se piu' utenti hanno stesso PIN, l'hash si calcola una sola volta.
        pin_hash_cache = {}

        for idx, row in enumerate(rows, start=1):
            if len(row) < 3:
                skipped += 1
                errors.append(f"Riga {idx}: campi insufficienti")
                continue

            name = row[0].strip()
            phone = row[1].strip()
            section = row[2].strip() or None
            role = row[3].strip() if len(row) > 3 and row[3].strip() else "rappresentante"
            pin = row[4].strip() if len(row) > 4 and row[4].strip() else "1234"

            if role not in ["admin", "rappresentante"]:
                role = "rappresentante"

            if not name or not phone:
                skipped += 1
                errors.append(f"Riga {idx}: nome o telefono/codice mancante")
                continue

            if pin not in pin_hash_cache:
                pin_hash_cache[pin] = fast_pin_hash(pin)

            pin_hash = pin_hash_cache[pin]

            if phone in existing_phones:
                cur.execute(
                    "UPDATE users SET name=?, section=?, role=?, pin_hash=?, active=1 WHERE phone=?",
                    (name, section, role, pin_hash, phone)
                )
                updated += 1
            else:
                cur.execute(
                    "INSERT INTO users(name, phone, section, role, pin_hash, qr_token, active, created_at) VALUES(?,?,?,?,?,?,1,?)",
                    (name, phone, section, role, pin_hash, secrets.token_urlsafe(12), now)
                )
                existing_phones.add(phone)
                imported += 1

        conn.commit()

    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({"ok": False, "error": f"Errore import CSV: {str(exc)}"}), 500

    conn.close()

    return jsonify({
        "ok": True,
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:10],
        "message": f"Import completato. Importati {imported}, aggiornati {updated}, saltati {skipped}."
    })


@app.patch("/api/users/<int:user_id>")
@admin_required
def update_user(user_id):
    data = request.get_json(force=True)

    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    section = str(data.get("section", "")).strip() or None
    role = str(data.get("role", "rappresentante")).strip()
    pin = str(data.get("pin", "")).strip()

    if not name or not phone:
        return jsonify({"ok": False, "error": "Nome e telefono/codice sono obbligatori"}), 400

    if role not in ["admin", "rappresentante"]:
        return jsonify({"ok": False, "error": "Ruolo non valido"}), 400

    conn = db()
    try:
        if pin:
            conn.execute(
                "UPDATE users SET name=?, phone=?, section=?, role=?, pin_hash=? WHERE id=?",
                (name, phone, section, role, generate_password_hash(pin), user_id)
            )
        else:
            conn.execute(
                "UPDATE users SET name=?, phone=?, section=?, role=? WHERE id=?",
                (name, phone, section, role, user_id)
            )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"ok": False, "error": "Telefono/codice gia' esistente"}), 409

    conn.close()
    return jsonify({"ok": True, "message": "Utente aggiornato correttamente"})

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
        "Elettori",
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
