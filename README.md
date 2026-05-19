# Comunali Barcellona P.G. - Web app con liste in tab

## Avvio locale
```bash
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

## Pannello admin
```text
/admin
```

## Deploy Render
Build command:
```bash
pip install -r requirements.txt
```

Start command:
```bash
gunicorn app:app
```

Environment variable consigliata:
```text
APP_SECRET_KEY=<chiave lunga casuale>
```


## Versione aggiornata
- campo note rimosso;
- admin può azzerare i voti con conferma scrivendo AZZERA;
- admin può aggiungere, disattivare/riattivare e rimuovere rappresentanti;
- admin può impostare elettori, votanti, numero consiglieri, sindaco eletto e modalità;
- dashboard con simulazione consiglieri eletti, soglia 5%, riparto seggi e premio di maggioranza.
