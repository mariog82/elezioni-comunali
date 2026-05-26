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


## Versione v13
- Candidati consiglieri presenti solo per:
  - Partito Democratico
  - Movimento 5Stelle
  - Città Aperta - Controcorrente
- Tutte le liste restano disponibili per i voti di lista.
- Dashboard admin:
  - torta candidati sindaco;
  - torta voti di lista;
  - istogramma voti di lista.
- Dettaglio per le tre liste:
  - voti di lista per seggio in istogramma;
  - voti candidati consiglieri per seggio in tab/istogrammi.


## Versione v14
- Grafico a torta delle liste con colori distinti per ciascuna lista.
- Grafico a torta dei sindaci con colori distinti.
- Istogramma delle liste spostato sotto i due grafici a torta.


## Versione v15
- Se il rappresentante accede a un seggio già chiuso, oltre al messaggio compare il pulsante:
  `Esci`.
- Il pulsante richiama `/api/logout`, elimina il cookie lato browser e riporta alla pagina iniziale.


## Versione v16
- L'amministratore può riattivare un seggio chiuso mantenendo tutti i dati aggiornati già presenti.
- La riattivazione azzera lo stato di chiusura (`closed=0`), cancella `closed_at` e aggiorna `updated_at`.
- Il rappresentante del seggio riattivato può accedere nuovamente e ritrova i dati già inviati al server.


## Versione v17
- Nel pannello amministratore il pulsante `Riapri seggio al rappresentante` viene visualizzato solo se il seggio risulta chiuso.
- Il pulsante riapre il seggio della sezione indicata mantenendo i dati già aggiornati.
- Se il seggio è aperto, viene mostrato solo lo stato `aperto`, senza pulsante di riapertura.


## Versione v18
- Solo l'amministratore visualizza campi input numerici per inserire direttamente i voti.
- I campi input sono disponibili per:
  - candidati sindaco;
  - voti di lista;
  - preferenze dei candidati consiglieri presenti.
- I rappresentanti vedono solo i pulsanti + e -.
- L'amministratore può usare sia input diretto sia pulsanti + e -.


## Versione v19
- Nei grafici a torta dei candidati sindaco è mostrata la percentuale sui votanti totali.
- Nel grafico a torta delle liste sono mostrati voti, percentuale sui votanti totali e seggi della lista.
- Nell'istogramma delle liste sono mostrati voti, percentuale sui votanti totali e numero di seggi.
- Se i votanti totali impostati dall'admin sono 0, viene usato il totale votanti rilevato dalle sezioni.


## Versione v20
- Anche i rappresentanti possono inserire direttamente i voti tramite campo numerico.
- Restano disponibili i pulsanti + e -.
- La lista `Movimento 2050` è stata rinominata in `Movimento 5Stelle`.


## Versione v21
- Corretto errore JavaScript che impediva il login:
  `Identifier 'inp' has already been declared`.
- Verificata sintassi di `app.js` con Node.
- Login ripristinato.


## Versione v23
- `Sindaco eletto / coalizione vincente` impostato di default su Nicola Barbera.
- Nicola Barbera è mostrato come primo candidato sindaco.
- Il calcolo dei seggi utilizza il valore inserito dall'amministratore nel campo `Consiglieri da eleggere`; default 24.
- Nella raccolta dati del seggio, `Schede contestate` è sostituito da `Numero di elettori`.
- Il numero di elettori del seggio è informativo e non entra nella quadratura votanti = validi + bianche + nulle.


## Versione v24
- Editing dei rappresentanti/utenti autorizzati dal pannello amministratore.
- È possibile modificare nome, telefono/codice, sezione, ruolo e PIN.
- Il PIN è opzionale: lasciandolo vuoto resta invariato.


## Versione v25
- Rimane disponibile il blocco per aggiungere rappresentante/utente.
- Nella lista utenti il pulsante `Salva modifiche` è sostituito da `Edit`.
- `Edit` apre un popup per modificare nome, telefono/codice, sezione, ruolo e PIN opzionale.


## Versione v26
- Importazione CSV dei rappresentanti / utenti autorizzati.
- Formato:
  nome;telefono/codice;sezione;ruolo;pin
- Separatore obbligatorio: ;
- PIN predefinito: 1234 se non indicato.


## Versione v27
- Reso visibile in modo esplicito nel pannello amministratore il blocco:
  `Importa rappresentanti / utenti da CSV`.
- Il blocco è posizionato sopra la lista `Rappresentanti / utenti autorizzati`.
- Pulsante: `Importa CSV rappresentanti/utenti`.


## Versione v29
- Corretto import CSV che restituiva HTML invece di JSON.
- Endpoint `/api/users/import-csv` registrato prima dell'avvio Flask.
- Import CSV ora crea nuovi utenti o aggiorna quelli esistenti con lo stesso telefono/codice.
- Risposta sempre JSON con conteggio importati, aggiornati e saltati.


## Versione v30
- Corretto timeout Render su `/api/users/import-csv`.
- Import CSV ottimizzato:
  - limite 1 MB;
  - massimo 500 righe per import;
  - parser CSV con separatore `;`;
  - cache degli hash dei PIN;
  - hashing PIN più leggero con `pbkdf2:sha256`.
- L'import resta transazionale: in caso di errore grave viene fatto rollback.


## Versione v31
- Corretto timeout Gunicorn/Render durante import CSV.
- Import massimo ridotto a 100 righe per volta.
- Limite file ridotto a 256 KB.
- Hash PIN ultra-leggero per import CSV: `pbkdf2:sha256:1`.
- Cache degli hash PIN ripetuti.
- Procfile aggiornato con `gunicorn --timeout 120 app:app`.


## Versione v32
- La sezione/seggio diventa la chiave logica del salvataggio.
- Primo invio di una sezione/seggio: nuovo record.
- Invii successivi sulla stessa sezione/seggio: aggiornamento del record esistente.
- Aggiunto indice unico `idx_reports_section_unique` su `reports(section)`.
- In caso di duplicati storici, viene conservato il record più recente per sezione.


## Versione v33
- Nuovo import CSV amministratore per dati sezione:
  `Sezione;Elettori;Votanti`
- Se la sezione esiste: aggiorna elettori e votanti.
- Se la sezione non esiste: crea il record sezione con voti iniziali a 0.
- Gli elettori sono salvati nel campo interno `contested_ballots` per compatibilità con le versioni precedenti, ma visualizzati come `Numero di elettori`.


## Versione v34
- Aggiunta pagina separata `/admin/tools` per grafici, importazioni CSV e gestione utenti.
- Aggiunti import CSV multipli per liste, sindaci, consiglieri e schede, sia totali sia per sezione.
- Gli import senza sezione aggiornano la sezione speciale `TOTALE`.
- Gli import per sezione creano o aggiornano il record della sezione.


## Versione v35
- Pannello admin principale alleggerito.
- Rimosse dal pannello principale:
  - grafici principali;
  - grafici dettaglio per seggio;
  - import dati sezioni;
  - import rappresentanti/utenti;
  - gestione utenti.
- Nuove pagine:
  - `/admin/charts` tramite pulsante `Grafici`;
  - `/admin/imports` tramite pulsante `Importazione`;
  - `/admin/users` tramite pulsante `Gestione utenti`.


## Versione v36
- Corretto errore `cannot read properties of null`.
- Il JavaScript amministratore ora funziona correttamente nelle pagine separate:
  `/admin`, `/admin/charts`, `/admin/imports`, `/admin/users`.


## Versione v37
- Nell'importazione dei voti di lista l'attribuzione avviene confrontando prioritariamente il `Nome Lista` nel CSV.
- Il `Numero Liste` viene usato solo come fallback.
- Il confronto ignora maiuscole/minuscole, accenti, spazi e punteggiatura.


## Versione v38
- In `app.py` i dati elettorali principali sono stati trasformati in maiuscolo.
- Sostituita `ù` con `U'`.
- Sostituita `à` con `A'`.
- La trasformazione è stata applicata senza rendere maiuscole le parole chiave Python, per non rompere l'esecuzione dell'applicazione.


## Versione v39
- Nell'import CSV il confronto di `Nome Lista` avviene tutto in minuscolo/normalizzato.
- Nell'import CSV il confronto di `Nome Cons` avviene tutto in minuscolo/normalizzato.
- Il numero lista e il numero consigliere restano fallback se il nome non viene riconosciuto.


## Versione v40
- Dopo il caricamento CSV, i voti delle liste vengono assegnati confrontando `Nome Lista` con i nomi presenti in `ELECTION_DATA` dentro `app.py`.
- I voti dei consiglieri vengono assegnati confrontando `Nome Cons` con i candidati presenti in `ELECTION_DATA` dentro `app.py`.
- `Numero Liste` e `Numero Cons` non vengono più usati per attribuire il voto, evitando associazioni errate.
- Il confronto è normalizzato: minuscolo, senza accenti, senza spazi/punteggiatura.
