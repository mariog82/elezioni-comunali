# ================================================================
# APP FLASK PER RACCOLTA, CONTROLLO E CALCOLO RISULTATI ELETTORALI
# ================================================================
# File commentato in modo esteso.
#
# Obiettivo dell'applicazione:
# - consentire ai rappresentanti di sezione di inserire i dati del seggio;
# - salvare voti a sindaco, voti di lista e preferenze in un database SQLite;
# - permettere all'amministratore di consultare dashboard, sezioni, utenti, esportazioni CSV;
# - calcolare soglie, coalizioni ammesse, premio di maggioranza e ripartizione dei seggi.
#
# PUNTI RICHIESTI:
# - Il calcolo del premio/voto di maggioranza è marcato con il commento: VOTO MAGGIORANZA.
# - Il calcolo della ripartizione dei seggi è marcato con il commento: DISTRIBUZIONE SEGGI.
# ================================================================

# Librerie standard per leggere/scrivere file CSV e gestire flussi testuali in memoria.
import csv
import io

# Componenti Flask usati per creare l'app web, gestire richieste HTTP, sessioni e risposte JSON/CSV.
from flask import Flask, request, jsonify, send_from_directory, session, Response
# Funzioni Werkzeug per salvare PIN/password in forma hashata e verificarli al login.
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import sqlite3, os, secrets, math

# Percorso assoluto della cartella in cui si trova questo file. Serve per costruire percorsi portabili.
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "database.sqlite")
STATIC_DIR = os.path.join(APP_DIR, "static")

# Istanza principale dell'applicazione Flask.
# static_folder indica la cartella dei file statici; static_url_path vuoto consente di servire index.html dalla root.
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")
app.secret_key = os.environ.get("APP_SECRET_KEY", secrets.token_hex(32))

# Struttura dati statica dell'elezione.
# Contiene:
# - l'elenco dei candidati sindaco;
# - l'elenco delle liste;
# - per ogni lista, la coalizione di riferimento e i candidati al consiglio.
# Questa struttura è usata sia per generare le schede di inserimento dati sia per calcolare eletti e seggi.
ELECTION_DATA = {
  "mayors": [
    "Nicola Barbera",
    "David Bongiovanni",
    "Melangela Scolaro"
  ],
  "lists": {
    "Lista 01 - Città Aperta - Controcorrente": {
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
    "Lista 012 - Movimento 5Stelle": {
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
    "Lista 010 - Partito Democratico": {
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
    "Lista 8 - De Luca Sindaco di Sicilia": {
      "coalition": "Melangela Scolaro",
      "candidates": []
    },
    "Lista 5 - Avremo Cura di Te": {
      "coalition": "Melangela Scolaro",
      "candidates": []
    },
    "Lista 16 - Scolaro Sindaco": {
      "coalition": "Melangela Scolaro",
      "candidates": []
    },
    "Lista 4 - Una Marcia in Più": {
      "coalition": "Melangela Scolaro",
      "candidates": []
    },
    "Lista 13 - Barcellona Pozzo di Gotto in Comune": {
      "coalition": "Melangela Scolaro",
      "candidates": []
    },
    "Lista 15 - Fratelli d’Italia": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Lista 14 - Nicola Barbera Sindaco": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Lista 17 - Lista Civica": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Lista 9 - Fuori dal Coro": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Lista 3 - Ascoltiamo Barcellona": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Lista 7 - Noi Ci Siamo": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Lista 11 - Forza Italia": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Lista 6 - Azzurri per Barcellona P.G.": {
      "coalition": "Nicola Barbera",
      "candidates": []
    },
    "Lista 2 - Vamos! Con Barbera Sindaco": {
      "coalition": "Nicola Barbera",
      "candidates": []
    }
  }
}

# ----------------------------------------------------------------
# Hash veloce del PIN
# ----------------------------------------------------------------
# Usato soprattutto nell'importazione CSV degli utenti.
# Riduce il costo computazionale dell'hashing per evitare timeout su ambienti hosting lenti.
def fast_pin_hash(pin):
    # Import CSV: hashing volutamente leggero per evitare timeout su Render.
    # check_password_hash resta compatibile con questo formato Werkzeug.
    return generate_password_hash(str(pin), method="pbkdf2:sha256:1", salt_length=4)

# ----------------------------------------------------------------
# Connessione al database SQLite
# ----------------------------------------------------------------
# Restituisce una connessione al database impostando row_factory=sqlite3.Row,
# così le righe possono essere lette anche per nome colonna, ad esempio row['name'].
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ----------------------------------------------------------------
# Inizializzazione del database
# ----------------------------------------------------------------
# Crea, se mancanti, le tabelle principali:
# - users: utenti, admin e rappresentanti di sezione;
# - reports: verbali/rilevazioni di sezione;
# - votes: voti a sindaco, voti di lista e preferenze;
# - settings: parametri generali dell'elezione.
# Include anche migrazioni leggere per database creati con versioni precedenti.
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
        "winner_mayor": "Nicola Barbera",
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

# Prima di ogni richiesta HTTP, Flask verifica che il database esista.
# Se il file SQLite non è presente, viene creato e inizializzato.
@app.before_request
def ensure_db():
    if not os.path.exists(DB_PATH):
        init_db()

# Recupera l'utente attualmente autenticato dalla sessione Flask.
# Se non esiste una sessione valida o l'utente è disattivato, restituisce None.
def current_user():
    user_id = session.get("uid")
    if not user_id:
        return None
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE id=? AND active=1", (user_id,)).fetchone()
    conn.close()
    return user

# Restituisce solo i dati utente che possono essere inviati al frontend.
# Non espone hash del PIN, token QR o altri dati interni.
def public_user(user):
    return {"id": user["id"], "name": user["name"], "phone": user["phone"], "role": user["role"], "section": user["section"]}

# Decoratore di protezione delle route.
# Blocca l'accesso alle API se l'utente non ha effettuato il login.
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return jsonify({"ok": False, "error": "Accesso non autorizzato"}), 401
        return fn(*args, **kwargs)
    return wrapper

# Decoratore di protezione per le funzioni riservate all'amministratore.
# Prima controlla l'autenticazione, poi verifica che role == 'admin'.
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

# Legge dal database le impostazioni generali dell'elezione.
# Restituisce valori convertiti nei tipi corretti: interi per elettori/votanti/seggi, stringhe per sindaco vincitore e modalità.
def get_settings(conn):
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    settings = {r["key"]: r["value"] for r in rows}
    return {
        "total_electors": int(settings.get("total_electors", "0") or 0),
        "total_voters": int(settings.get("total_voters", "0") or 0),
        "council_seats": int(settings.get("council_seats", "24") or 24),
        "winner_mayor": settings.get("winner_mayor", "Nicola Barbera"),
        "mode": settings.get("mode", "first"),
    }

# ----------------------------------------------------------------
# DISTRIBUZIONE SEGGI - Metodo D'Hondt
# ----------------------------------------------------------------
# Questa funzione riceve un dizionario di voti, per esempio:
#   {'Coalizione A': 1000, 'Coalizione B': 700}
# e il numero di seggi da distribuire.
#
# Per ogni lista/coalizione calcola i quozienti: voti/1, voti/2, voti/3, ...
# Ordina tutti i quozienti in modo decrescente e assegna i seggi ai primi N quozienti,
# dove N è il numero totale di seggi disponibili.
#
# Il risultato è un dizionario con il numero di seggi assegnati a ciascun soggetto.
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

# ----------------------------------------------------------------
# Calcolo complessivo del risultato elettorale
# ----------------------------------------------------------------
# Questa funzione aggrega i voti salvati nel database, applica soglia di sbarramento,
# calcola i voti di coalizione, attribuisce i seggi, applica l'eventuale premio
# di maggioranza e individua i candidati eletti in base alle preferenze.
def compute_elected(conn):
    # Lettura dei parametri di configurazione: numero seggi, sindaco vincitore, modalità elettorale.
    settings = get_settings(conn)
    # Numero di seggi del consiglio comunale. max(1, ...) evita valori nulli o negativi.
    seats = max(1, settings["council_seats"])
    # Sindaco vincitore impostato dall'amministratore.
    # È il riferimento per calcolare l'eventuale premio di maggioranza.
    winner = settings["winner_mayor"]
    # Modalità elettorale: 'first' per primo turno, 'runoff' per ballottaggio.
    mode = settings["mode"]
    # Aggregazione dei voti di lista su tutte le sezioni.
    list_rows = conn.execute("SELECT list_name AS name, SUM(votes) AS total FROM votes WHERE vote_type='lista' GROUP BY list_name").fetchall()
    # Aggregazione delle preferenze personali dei candidati, raggruppate per lista e nome candidato.
    pref_rows = conn.execute("SELECT list_name, name, SUM(votes) AS total FROM votes WHERE vote_type='preferenza' GROUP BY list_name, name").fetchall()
    # Aggregazione dei voti ai candidati sindaco.
    mayor_rows = conn.execute("SELECT name, SUM(votes) AS total FROM votes WHERE vote_type='sindaco' GROUP BY name").fetchall()
    mayor_votes = {row["name"]: int(row["total"] or 0) for row in mayor_rows}
    list_votes = {row["name"]: int(row["total"] or 0) for row in list_rows}
    # Totale generale dei voti validi di lista. È la base per soglia e percentuali.
    total_list_votes = sum(list_votes.values())
    # Soglia di sbarramento al 5% dei voti di lista complessivi.
    threshold = total_list_votes * 0.05
    # Liste ammesse alla ripartizione: devono avere voti positivi e superare la soglia.
    admitted_lists = {name: votes for name, votes in list_votes.items() if votes > 0 and votes >= threshold}
    # Somma dei voti delle liste ammesse, raggruppati per coalizione/sindaco collegato.
    coalition_votes = {}
    for list_name, votes in admitted_lists.items():
        coalition = ELECTION_DATA["lists"][list_name]["coalition"]
        coalition_votes[coalition] = coalition_votes.get(coalition, 0) + votes
    # DISTRIBUZIONE SEGGI
    # Prima ripartizione naturale dei seggi tra coalizioni con metodo D'Hondt.
    # In questa fase non è ancora applicato il premio di maggioranza.
    coalition_seats = d_hondt(coalition_votes, seats) if coalition_votes else {}
    # Voti di coalizione attribuiti al sindaco vincitore.
    winner_coal_votes = coalition_votes.get(winner, 0)
    # VOTO MAGGIORANZA
    # Percentuale della coalizione del sindaco vincitore sul totale dei voti di lista.
    # Questo valore viene usato per verificare se il vincitore ha almeno il 40% al primo turno
    # oppure se, in caso di ballottaggio, può accedere al premio secondo la logica implementata.
    winner_pct = (winner_coal_votes / total_list_votes * 100) if total_list_votes else 0
    # VOTO MAGGIORANZA
    # Percentuale massima raggiunta da una coalizione diversa da quella del sindaco vincitore.
    # Serve a evitare il premio se un'altra coalizione supera il 50%.
    other_max_pct = max([v / total_list_votes * 100 for c, v in coalition_votes.items() if c != winner] or [0]) if total_list_votes else 0
    # VOTO MAGGIORANZA
    # Numero minimo di seggi garantiti alla coalizione vincente in caso di premio di maggioranza.
    # Qui è fissato al 60% dei seggi, arrotondato per eccesso.
    premium_seats = math.ceil(seats * 0.60)
    # Seggi che la coalizione vincente otterrebbe senza premio, cioè con la sola ripartizione D'Hondt.
    natural_winner_seats = coalition_seats.get(winner, 0)
    # VOTO MAGGIORANZA
    # Condizione centrale del premio di maggioranza.
    # Il premio viene applicato solo se:
    # 1) la coalizione vincente non ha già almeno il 60% dei seggi;
    # 2) nessuna altra coalizione supera il 50%;
    # 3) si è in modalità ballottaggio oppure la coalizione vincente ha almeno il 40% al primo turno.
    premium_applied = natural_winner_seats < premium_seats and other_max_pct <= 50 and (mode == "runoff" or winner_pct >= 40)
    # VOTO MAGGIORANZA
    # Se le condizioni sono rispettate, viene forzata l'assegnazione del numero minimo
    # di seggi alla coalizione del sindaco vincitore.
    if premium_applied:
        # Alla coalizione del sindaco vincitore vengono assegnati i seggi del premio.
        coalition_seats[winner] = premium_seats
        # I seggi rimanenti sono distribuiti proporzionalmente alle altre coalizioni.
        remaining_seats = seats - premium_seats
        other_coalitions = {coalition: votes for coalition, votes in coalition_votes.items() if coalition != winner}
        # DISTRIBUZIONE SEGGI
        # Ripartizione dei soli seggi residui tra le coalizioni non vincenti.
        other_seats = d_hondt(other_coalitions, remaining_seats) if other_coalitions and remaining_seats > 0 else {}
        for coalition in other_coalitions:
            coalition_seats[coalition] = other_seats.get(coalition, 0)
    # DISTRIBUZIONE SEGGI
    # Dizionario finale dei seggi assegnati alle singole liste.
    # Dopo aver stabilito quanti seggi spettano a ciascuna coalizione, i seggi della coalizione
    # vengono distribuiti tra le liste interne alla coalizione stessa.
    list_seats = {}
    for coalition, coalition_seat_count in coalition_seats.items():
        lists_in_coalition = {list_name: votes for list_name, votes in admitted_lists.items() if ELECTION_DATA["lists"][list_name]["coalition"] == coalition}
        # DISTRIBUZIONE SEGGI
        # Ripartizione interna dei seggi della coalizione tra le sue liste ammesse.
        assigned = d_hondt(lists_in_coalition, coalition_seat_count) if lists_in_coalition and coalition_seat_count > 0 else {}
        list_seats.update(assigned)
    # Costruzione di una struttura rapida per recuperare le preferenze di ogni candidato per lista.
    preferences = {}
    for row in pref_rows:
        preferences.setdefault(row["list_name"], {})[row["name"]] = int(row["total"] or 0)
    # Individuazione degli eletti: per ogni lista si ordinano i candidati per preferenze decrescenti.
    # In caso di parità, resta l'ordine di lista originario.
    elected = {}
    for list_name, list_obj in ELECTION_DATA["lists"].items():
        count = list_seats.get(list_name, 0)
        ranked = []
        for index, candidate in enumerate(list_obj["candidates"]):
            ranked.append({"name": candidate, "votes": preferences.get(list_name, {}).get(candidate, 0), "order": index + 1})
        ranked.sort(key=lambda item: (-item["votes"], item["order"]))
        elected[list_name] = ranked[:count]
    # Elenco dei candidati sindaco non vincenti, ordinati per voti.
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

# Route pubblica principale: restituisce la pagina index.html della web app.
@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")

# Route della pagina di amministrazione.
@app.route("/admin")
def admin_page():
    return send_from_directory(STATIC_DIR, "admin.html")

# API di login: accetta telefono/PIN oppure token QR e salva l'id utente in sessione.
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

# API di logout: elimina la sessione Flask.
@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

# Restituisce i dati dell'utente attualmente autenticato.
@app.get("/api/me")
@login_required
def me():
    return jsonify({"ok": True, "user": public_user(current_user())})

# Restituisce al frontend la configurazione elettorale e le impostazioni generali.
@app.get("/api/config")
@login_required
def config():
    conn = db()
    settings = get_settings(conn)
    conn.close()
    return jsonify({"ok": True, "data": ELECTION_DATA, "settings": settings})


# Recupera l'ultimo report/voto inserito per una determinata sezione.
# Serve al rappresentante per ritrovare i dati già salvati e modificarli prima della chiusura.
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
        "section_electors": report["contested_ballots"],
        "contested_ballots": report["contested_ballots"],
        "closed": bool(report["closed"]),
        "closed_at": report["closed_at"],
        "mayors": mayors,
        "list_votes": list_votes,
        "preferences": preferences,
        "updated_at": report["updated_at"]
    })

# Salvataggio parziale del report di sezione.
# Non chiude il seggio: consente invii progressivi e correzioni.
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
    existing = cur.execute("SELECT id, closed FROM reports WHERE user_id=? AND section=?", (user["id"], section)).fetchone()
    if existing and user["role"] != "admin" and existing["closed"]:
        conn.close()
        return jsonify({"ok": False, "error": "Il seggio risulta già chiuso. Non puoi più modificare o inviare dati."}), 403
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


# Verifica se una sezione risulta chiusa.
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

# Chiusura definitiva del seggio da parte del rappresentante.
# Prima di chiudere controlla la quadratura tra votanti, voti validi, schede bianche e nulle.
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
    existing = cur.execute("SELECT id, closed FROM reports WHERE user_id=? AND section=?", (user["id"], section)).fetchone()
    if existing and existing["closed"]:
        conn.close(); return jsonify({"ok": False, "error": "Il seggio è già chiuso."}), 403
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

# Riapertura amministrativa di una sezione già chiusa.
# Permette al rappresentante di correggere dati già inviati.
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

    # Riattiva il seggio mantenendo tutti i dati già aggiornati presenti nel database.
    cur.execute(
        "UPDATE reports SET closed=0, closed_at=NULL, updated_at=? WHERE section=?",
        (now, section)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "message": "Seggio riattivato con i dati aggiornati già presenti. Il rappresentante può nuovamente accedere e modificare."
    })



# Dashboard amministrativa.
# Aggrega voti, preferenze, riepiloghi di sezione e risultato elettorale calcolato.
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
    # Calcola soglie, premio di maggioranza, distribuzione seggi ed eletti.
    election = compute_elected(conn)
    conn.close()
    return jsonify({"ok": True, "mayors": [dict(row) for row in mayors], "lists": [dict(row) for row in lists], "preferences": [dict(row) for row in preferences], "sections": [dict(row) for row in sections], "ballot_totals": dict(ballot_totals), "data": ELECTION_DATA, "election": election})

# Aggiornamento delle impostazioni generali da pannello admin.
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

# Azzeramento completo dei voti e dei report. Richiede conferma testuale 'AZZERA'.
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

# Elenco utenti per il pannello amministrativo.
@app.get("/api/users")
@admin_required
def users():
    conn = db()
    rows = conn.execute("SELECT id, name, phone, role, section, qr_token, active FROM users ORDER BY id").fetchall()
    conn.close()
    return jsonify({"ok": True, "users": [dict(row) for row in rows]})

# Creazione manuale di un nuovo utente.
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







# Importazione utenti da file CSV.
# Consente di creare o aggiornare rappresentanti/admin in blocco.
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
            "error": "Troppe righe. Import massimo consentito: 100 utenti per volta. Dividi il CSV in più file."
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

        # Cache hashing: se più utenti hanno stesso PIN, l'hash si calcola una sola volta.
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


# Aggiornamento dati utente esistente.
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
        return jsonify({"ok": False, "error": "Telefono/codice già esistente"}), 409

    conn.close()
    return jsonify({"ok": True, "message": "Utente aggiornato correttamente"})

# Eliminazione utente. Non consente di eliminare l'utente attualmente collegato.
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

# Attivazione/disattivazione utente.
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


# Dettaglio completo per sezione: voti sindaco, voti lista e preferenze.
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

# Esportazione CSV dei dati elettorali aggregati per sezione e tipo di voto.
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

# Avvio diretto dell'applicazione quando il file viene eseguito con python app.py.
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
