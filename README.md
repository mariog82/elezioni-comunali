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


## Versione v4
- Le schede contestate NON entrano più nella quadratura dei votanti.
- Controllo corretto:
  votanti = voti validi + schede bianche + schede nulle.
- Le contestate sono registrate solo come dato informativo/indicativo.


## Versione v5
- Esportazione CSV corretta con separatore di campo `;`.
- I campi esportati sono separati formalmente tramite `csv.writer`.
- I nomi con spazi restano dentro il proprio campo.
- Intestazione CSV:
  Sezione;Rappresentante;Votanti;Bianche;Nulle;Contestate;Aggiornato;Tipo;Lista;Nome;Voti


## Versione v6
- CSV esportato con `sep=;` e `csv.writer` con delimitatore `;` per intestazione e righe dati.
- Aggiunti grafici per sezione/seggio:
  - voti di lista per seggio;
  - voti candidati sindaco per seggio;
  - preferenze dei candidati consiglieri per seggio, per ciascuna lista.


## Versione v7
- Tabelle candidato-preferenze in tab separate per lista.
- Ogni tab preferenze mostra tutti i candidati della lista, anche con 0 voti.
- Grafici di dettaglio separati in tab:
  - liste per seggio;
  - sindaci per seggio;
  - consiglieri per seggio.


## Versione v8
- L'invio al server centrale non è più bloccato dalla quadratura votanti.
- Nuovo pulsante Chiudi seggio: controlla la quadratura finale votanti = voti validi + bianche + nulle.
- Dopo la chiusura, il rappresentante non può più modificare o accedere al seggio.
- Popup di conferma e messaggio di ringraziamento.
- L'amministratore può riaprire un seggio chiuso.
- Nei grafici di dettaglio: liste per seggio e consiglieri per seggio sono in sotto-tab.


## Versione v9
- Invio dati libero per il rappresentante: la quadratura non blocca l'invio ordinario.
- Nuovo pulsante "Chiudi seggio" con popup di conferma.
- Alla chiusura viene controllata la quadratura finale: votanti = voti validi + bianche + nulle.
- Le schede contestate sono solo indicative.
- Dopo la chiusura il rappresentante visualizza un messaggio di ringraziamento e non può più modificare il seggio.
- Solo l'amministratore può riaprire il seggio.
- L'amministratore può modificare i dati anche dei seggi chiusi.
- Grafici di dettaglio raccolti in tab:
  - liste per seggio, con sotto-tab per ogni lista;
  - sindaci per seggio;
  - consiglieri per seggio, con sotto-tab per lista.


## Versione v10
- L'invio dati ordinario del rappresentante non è bloccato dalla quadratura.
- La quadratura blocca solo il pulsante "Chiudi seggio".
- Il campo sezione/seggio è bloccato per i rappresentanti di lista.
- Dopo ogni invio, il rappresentante ricarica automaticamente dal server i dati aggiornati del proprio seggio.
- Se il seggio è chiuso, il rappresentante vede il messaggio di ringraziamento e non può accedere alla modifica.


## Versione v11
- Corretto errore su `/api/export.csv`.
- Aggiunta migrazione automatica robusta per database SQLite già creati con versioni precedenti.
- Export CSV usa `sep=;` e `csv.writer` con delimitatore `;` per tutte le righe.


## Versione v12
- Corretto errore Render:
  `NameError: name 'io' is not defined`
- Aggiunti import mancanti:
  - import io
  - import csv
- Export CSV compatibile con Render/Gunicorn.
