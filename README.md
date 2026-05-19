# Comunali Barcellona P.G. - Web app v3

## Novità v3
- Per ogni sezione/seggio si inseriscono:
  - numero votanti;
  - schede bianche;
  - schede nulle;
  - schede contestate.
- Controllo obbligatorio prima dell'invio:
  - votanti = voti validi + schede bianche + schede nulle + schede contestate.
- Dashboard admin con quadratura generale delle sezioni.
- Tutte le liste in tab.
- Admin: reset voti, gestione utenti, parametri elettorali, simulazione seggi/eletti.

## Avvio locale Windows
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Aprire:
```text
http://localhost:5000
```

## Accessi demo
- Admin: `admin` / `1234`
- Rappresentante sezione 1: `3330000001` / `1111`
- Rappresentante sezione 2: `3330000002` / `2222`

## Deploy Render
Build Command:
```bash
pip install -r requirements.txt
```

Start Command:
```bash
gunicorn app:app
```

Environment Variable:
```text
APP_SECRET_KEY=<chiave_lunga_casuale>
```
