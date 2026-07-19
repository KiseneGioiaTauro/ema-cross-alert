# EMA Cross Alert — monitoraggio 24/7 via GitHub Actions + Telegram

Questo repository controlla in automatico, ogni 5 minuti, se una EMA veloce
incrocia una EMA lenta su un cambio forex (default EUR/USD, timeframe 5min,
EMA 34/144) e ti manda un messaggio Telegram quando succede. Gira su server
di GitHub, quindi funziona **anche se il telefono è spento, bloccato o senza
connessione**: il messaggio Telegram resta in coda e arriva appena il
telefono si riconnette.

Nessun costo: sia Twelve Data (piano free) sia GitHub Actions (per un job
così piccolo) sia Telegram sono gratuiti.

---

## 1. Crea un account GitHub

Vai su [github.com/join](https://github.com/join) e crea un account gratuito.

## 2. Crea un nuovo repository con questi file

- Su GitHub, clicca **New repository** (può essere pubblico o privato, va bene
  entrambi — le chiavi non finiscono mai nel codice, solo nei "Secrets").
- Carica dentro tutti i file e cartelle di questo pacchetto mantenendo la
  struttura:
  ```
  .github/workflows/check.yml
  scripts/check_cross.py
  state/last_candle.json
  requirements.txt
  README.md
  ```
  Il modo più semplice: sulla pagina del repo vuoto, usa "uploading an
  existing file" e trascina tutta la cartella (GitHub ricrea le sottocartelle
  automaticamente), oppure clona il repo e fai `git push` da terminale.

## 3. Crea il bot Telegram

1. Apri Telegram, cerca l'utente **@BotFather**.
2. Manda `/newbot`, scegli un nome e uno username (deve finire in `bot`).
3. BotFather ti dà un **token** tipo `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxx`.
   Copialo, ti servirà al passo 5.
4. Cerca il tuo nuovo bot su Telegram e mandagli un qualsiasi messaggio
   (es. "ciao") — è necessario per poter poi recuperare il tuo chat id.

## 4. Trova il tuo chat id

Apri questo link nel browser, sostituendo `<TOKEN>` con il token ottenuto da
BotFather:

```
https://api.telegram.org/bot<TOKEN>/getUpdates
```

Nel testo che compare cerca `"chat":{"id":123456789,...}` — quel numero è il
tuo `TELEGRAM_CHAT_ID`.

Se non vedi nulla, assicurati di aver mandato prima un messaggio al bot
(passo 3.4) e ricarica la pagina.

## 5. Configura i Secrets su GitHub

Nel repository: **Settings → Secrets and variables → Actions → Secrets →
New repository secret**. Aggiungi questi tre:

| Nome | Valore |
|---|---|
| `TWELVE_DATA_API_KEY` | la tua API key di Twelve Data |
| `TELEGRAM_BOT_TOKEN` | il token ottenuto da BotFather |
| `TELEGRAM_CHAT_ID` | il numero ottenuto al passo 4 |

## 6. (Opzionale) Personalizza simbolo, timeframe ed EMA

Stessa pagina, ma tab **Variables** invece di **Secrets** → **New repository
variable**. Se non le imposti, vengono usati i valori di default (EUR/USD,
5min, EMA 34/144).

| Nome | Esempio | Default se non impostata |
|---|---|---|
| `SYMBOL` | `GBP/USD`, `USD/JPY`, `BTC/USD` | `EUR/USD` |
| `INTERVAL` | `1min`, `15min`, `1h`, `1day` | `5min` |
| `FAST_PERIOD` | `21` | `34` |
| `SLOW_PERIOD` | `200` | `144` |

## 7. Abilita e testa il workflow

1. Vai sul tab **Actions** del repository. Se richiesto, clicca "I understand
   my workflows, go ahead and enable them".
2. Seleziona il workflow **EMA Cross Check** nella lista a sinistra.
3. Clicca **Run workflow** per un test manuale immediato.
4. Apri il log dell'esecuzione: dovresti vedere il prezzo e i valori EMA
   stampati. Se hai configurato Telegram correttamente e (per puro caso) c'è
   stato un incrocio proprio ora, ricevi subito il messaggio.

Da questo momento il workflow gira da solo ogni 5 minuti, senza bisogno di
aprire nulla su telefono o PC.

---

## Cose da sapere

- **Precisione del cron**: GitHub non garantisce che `*/5 * * * *` scatti
  esattamente ogni 5 minuti al secondo — sotto carico può ritardare di
  qualche minuto. Per un'analisi a 5 minuti è comunque adeguato.
- **Limiti Twelve Data free**: 8 richieste/minuto e 800/giorno. Con un
  controllo ogni 5 minuti usi circa 288 richieste al giorno: ampio margine.
- **Limiti GitHub Actions free**: sui repository pubblici i minuti sono
  illimitati; su repository privati hai 2.000 minuti/mese gratuiti — questo
  job dura pochi secondi a esecuzione, quindi non li esaurisci.
- **Dispositivo davvero spento**: nessun sistema può recapitare una notifica
  a un telefono spento. Il vantaggio di questa architettura è che il
  controllo e l'invio avvengono comunque, e il messaggio ti aspetta in
  Telegram appena riaccendi il telefono o torni online.
- **Sicurezza**: le chiavi restano nei "Secrets" di GitHub, mai visibili nel
  codice o nei log.
- Vuoi anche l'app/PWA sul telefono per un controllo visivo in tempo reale?
  Puoi usarla insieme a questo sistema: la PWA per guardare il grafico
  quando hai il telefono in mano, questo workflow come rete di sicurezza
  che avvisa anche quando non stai guardando.
