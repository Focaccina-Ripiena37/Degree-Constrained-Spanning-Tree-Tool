# 🌳 DCST Tool – Risolutore per l’Albero di Copertura con Vincolo di Grado (DCMST)

> Nota (11/2025): questo repository adotta un profilo accademico semplificato, incentrato su chiarezza e didattica.
> Include una GUI Tkinter minimale e tre algoritmi (Greedy, Local Search, Simulated Annealing).
> Sistemi avanzati (tracciamento performance, parallelizzazione adattiva, packaging pesante, splash/temi) sono stati rimossi o deprecati.
> I risultati (grafi, alberi, tabelle, grafici dello score) sono salvati come immagini nella cartella Desktop/Plot/.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Piattaforme](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool)
[![Licenza](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Build](https://img.shields.io/badge/Build-Passing-brightgreen.svg)](BUILD_INSTRUCTIONS.md)
[![Stile: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://black.readthedocs.io/en/stable/)
[![Test](https://img.shields.io/badge/tests-6%20passing-brightgreen.svg)](../../actions)
[![PR benvenute](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](../../blob/main/CONTRIBUTING.md)

**DCST Tool** è una piccola applicazione grafica, adatta a studenti, sviluppata in Python per il problema del **Degree-Constrained Minimum Spanning Tree (DCMST)**. Nel profilo semplificato l’attenzione è su chiarezza, coerenza e visualizzazione dei risultati.

## Dependencies (minimal)

- Required: `networkx`, `matplotlib`
- Optional: `pandas` (only for saving the combined summary table image; the app runs fine without it)

Install with:

```
pip install -r requirements.txt
```

## 📋 Problema

Dato un grafo pesato e non necessariamente completo e un nodo radice r, trovare un albero di copertura minimo radicato in r tale che ogni nodo abbia al più k figli (vincolo di grado).

```
INPUT:  Grafo pesato G = (V, E), nodo radice r, vincolo di grado k
OUTPUT: Albero di copertura T a costo minimo che rispetta il vincolo di grado (soft con penalità)
```

<img width="601" height="789" alt="Screenshot 2025-11-03 164249" src="https://github.com/user-attachments/assets/44a56a68-af2a-4813-955f-dc065bb47bfa" />

## 🎯 Approcci algoritmici

Il tool implementa e confronta tre strategie per il problema DCMST:

### 🔧 **Greedy (radicata, consapevole del grado, vincolo soft)**
- **Tipo**: Costruttiva (stile Prim)
- **Idea**: Cresce dall’origine aggiungendo l’arco di frontiera più economico che tenga i gradi ≤ k su entrambi i capi. Se non esistono tali archi ma il grafo non è ancora connesso, usa un fallback che minimizza peso + λ·eccesso (vincolo soft), garantendo la connettività.
- **Radice**: di default R = 0.
- **Implementazione**: due heap (preferiti vs fallback); i preferiti rispettano k, il fallback usa un costo “effettivo” con penalità per l’eccesso di grado.
- **Caratteristiche**: molto veloce; preferisce soluzioni ammissibili ma può superare k con penalità per completare l’albero.
- **Complessità**: O(E log V)

### 🔄 **Hill Climbing (ricerca locale a primo miglioramento campionato)**
- **Tipo**: Metaeuristica di ricerca locale
- **Idea**: a ogni iterazione campiona fino a m archi non in albero; per ciascuno prova una mossa di edge-swap e accetta il primo miglioramento sull’obiettivo (costo + λ·eccesso).
- **Tuning**: m impostabile in Modalità Avanzata (default m = 10)
- **Caratteristiche**: migliora rapidamente Greedy; si ferma in un ottimo locale quando non trova miglioramenti nel campione.
- **Terminazione**: nessun vicino migliore nel campione dell’iterazione.

### 🔥 **Simulated Annealing**
- **Tipo**: Metaeuristica probabilistica
- **Idea**: edge-swap sull’obiettivo penalizzato (costo + λ·eccesso), con accettazione probabilistica in base alla temperatura.
- **Implementazione**: accetta sempre i miglioramenti, accetta peggioramenti con probabilità exp(−Δ/T).
- **Caratteristiche**: esce dagli ottimi locali ed esplora di più.
- **Raffreddamento**: esponenziale (T = T × α).

## ✨ Funzionalità

### 🖥️ **GUI (semplificata)**
- Interfaccia Tkinter essenziale con parametri base (sinistra) e Modalità Avanzata opzionale (destra) per SA/LS
- Barra di progresso deterministica e piccolo riquadro log
- Output salvati in Desktop/Plot/ (creata automaticamente); bottone “Apri Cartella Plot” per aprire la cartella

### 📊 **Analisi e visualizzazione**
- Visualizzazione del grafo e degli alberi (NetworkX + Matplotlib)
- Immagine tabellare di confronto e grafico dell’evoluzione dello score
- Metriche base: costo, tempo di esecuzione, violazioni del vincolo di grado

### 🚀 Packaging
- Il packaging in eseguibili non rientra nell’attuale profilo semplificato.

## 📦 Installazione e uso

### 🎯 **Per utenti finali**
Il packaging binario non è previsto nel profilo semplificato. Usa la procedura per sviluppatori qui sotto. Su Windows puoi anche eseguire `install_dependencies.cmd` per creare il virtualenv e installare i requisiti (aggiungi `--with-pandas` per abilitare l’immagine tabellare opzionale).

### 🛠️ **Per sviluppatori**

#### Prerequisiti
- Python 3.10 o superiore
- Gestore pacchetti pip
- Git (per il clone)

#### Procedura di installazione
```
# Clone
git clone https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.git
cd Degree-Constrained-Spanning-Tree-Tool

# Crea e attiva un virtual environment (consigliato)
python -m venv .venv
\.\.venv\Scripts\Activate.ps1  # Windows PowerShell

# Installa le dipendenze minime
pip install -r requirements.txt

# (Opzionale) Installa extra per l’immagine tabellare
# pip install pandas

# Esegui i test (opzionale)
python -m pytest -q

# Avvia l’applicazione
python run.py
```

#### Setup per piattaforma

**Windows:**
```cmd
# Avvio rapido (PowerShell)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; python run.py

# In alternativa, script guidato (crea .venv e installa dipendenze):
./install_dependencies.cmd
```

**macOS:**
```bash
# Crea e attiva il venv, poi installa ed esegui
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python run.py
```

**Linux:**
```bash
# Installa le dipendenze
pip3 install -r requirements.txt

# Avvia l’applicazione
python3 run.py
```

## 🎮 Istruzioni d’uso

### Flusso base
1. **Avvio**: esegui DCST Tool (niente splash screen)
2. **Configura i parametri**:
   - dimensioni dei grafi (Small: 10, Medium: 50, Large: 200 nodi)
   - vincolo di grado k (figli massimi per nodo)
   - penalità per le violazioni del vincolo
   - probabilità di connessione p
3. **Esegui gli algoritmi**: premi “Start” per lanciare Greedy, Local e SA
4. **Monitora**: segui la barra di avanzamento e i messaggi di log
5. **Visualizza**: analizza i grafi, gli alberi e le metriche
6. **Esporta**: i risultati sono salvati in `~/Desktop/Plot/`

### Configurazione avanzata
- Modalità Avanzata: regola temperatura di SA, fattore di raffreddamento, iterazioni e campione m di Local Search
- Stop: interrompe esecuzioni lunghe

### Perché i risultati possono apparire “piatti” con i valori di default
I valori di default sono pensati per una esecuzione rapida e robusta in aula o su laptop. Su grafi relativamente piccoli e con parametri moderati, la Greedy con vincolo soft tende già a produrre soluzioni vicine all’ottimo penalizzato, e le metaeuristiche (Local/SA) possono mostrare miglioramenti marginali. Questo può far sembrare che “tutti gli algoritmi vadano uguale”.

Per evidenziare meglio le differenze tra algoritmi, prova a variare i parametri e “giocare” con questi fattori:

- Dimensione del grafo: alza “Media/Grande” (es. 80–200 nodi) per ampliare lo spazio delle soluzioni.
- Densità (prob. di connessione p): valori intermedi (0.2–0.5) generano più alternative plausibili; valori troppo bassi forzano collegamenti, troppo alti appiattiscono i margini di miglioramento.
- Vincolo di grado k: rendilo più stringente (es. k=2 o 3). Un vincolo “tight” crea conflitti che la ricerca locale/SA può gestire meglio.
- Penalità λ (Parametro “Penalità”): aumentando λ aumenti il costo delle violazioni; con λ più alto le differenze nelle strategie emergono più chiaramente.
- Local Search: aumenta m (campione dell’intorno) e/o le iterazioni per cercare miglioramenti più profondi.
- Simulated Annealing: usa temperature iniziali più alte, riduzioni più lente (α vicino a 0.99) e più iterazioni per esplorare di più (maggiore capacità di uscire dai minimi locali).

Suggerimento pratico: parti da Small/Medium, k=2 o 3, p≈0.3–0.4, penalità 1000–5000, LS con m=20–40, SA con T0=200–400, α=0.97–0.99, iterazioni 2000–5000. Osserva l’evoluzione del costo/score e confronta i grafi salvati.

### File di output
I risultati sono salvati su Desktop nella cartella `Plot/`:
- **Grafi iniziali**: visualizzazione dei grafi generati
- **Alberi ottimizzati**: alberi trovati da ciascun algoritmo
- **Tabella di confronto**: metriche e qualità della soluzione
- **Grafici dello score**: andamento dello score nel tempo
- **Log dettagliati**: statistiche d’esecuzione e violazioni del vincolo

## 🔧 Packaging in eseguibili
Non previsto nel profilo semplificato attuale (possibile elemento di roadmap).

## 📊 Requisiti di sistema

### Minimi richiesti
- **RAM**: 4 GB (8 GB consigliati)
- **Storage**: 500 MB liberi
- **CPU**: qualunque processore moderno (multi-core consigliato per grafi grandi)

### Compatibilità piattaforme
- **Windows**: Windows 10/11 (64-bit) ✅
- **macOS**: macOS 10.14+ ✅
- **Linux**: principali distribuzioni moderne (64-bit) ✅

### Linee guida prestazionali
- **Grafi piccoli** (< 50 nodi): tutti gli algoritmi vanno bene su qualunque macchina
- **Grafi medi** (50–200 nodi): buone prestazioni con i default
- **Grafi grandi** (200+ nodi): può servire tuning e hardware più potente

## 🧪 Stack tecnologico

### Tecnologie principali
- **Python 3.10+**
- **Tkinter** (GUI multipiattaforma)
- **NetworkX** (grafi e algoritmi)
- **Matplotlib** (visualizzazione)
- **(Opzionale) Pandas** (immagine tabellare combinata)

### Librerie aggiuntive
- **PIL/Pillow**: elaborazione immagini (tramite Matplotlib)

### Strumenti di build
- (rimandati nel profilo semplificato)

## 📚 Documentazione
Alcuni documenti storici possono citare funzionalità avanzate non più presenti.

### Documentazione algoritmica
Gli algoritmi seguono approcci standardizzati:
- **Greedy**: espansione stile Prim radicata e consapevole del grado con vincolo soft (R=0 di default)
- **Hill Climbing**: primo miglioramento su vicinato di edge-swap (obiettivo penalizzato)
- **Simulated Annealing**: raffreddamento esponenziale con accettazione probabilistica; mosse su edge-swap

### Punteggio (MAUT, utilità esponenziale, log su tempo/memoria)

Per confrontare soluzioni con attributi eterogenei (costo, tempo, memoria) il tool utilizza una funzione di punteggio accademica basata sulla Multi-Attribute Utility Theory (MAUT) con:

- combinazione additiva pesata delle componenti (costo, tempo, memoria);
- trasformazione logaritmica su tempo e memoria (rendimenti decrescenti su scale fortemente asimmetriche);
- utility esponenziale negativa per comprimere code alte e garantire output in [0,100].

Riferimenti essenziali: Keeney & Raiffa (1976), “Decisions with Multiple Objectives: Preferences and Value Tradeoffs”.

Formula (sintesi):

- Costo effettivo: C_eff = cost + λ · violations
- Perdita aggregata: L = w_cost · (C_eff / cost_ref) + w_time · ln(1 + time_s / time_ref) + w_mem · ln(1 + memory_mb / memory_ref)
- Punteggio (mapping): score = 100 · exp(-L)  (oppure 100/(1+L))

Valori di riferimento (indipendenti dal confronto tra algoritmi):

- cost_ref: costo atteso/baseline (nel tool: costo Greedy dell’istanza, se disponibile)
- time_ref: 0.1 s (tempo “accettabile” per le immagini/tabella generate dall’app);
   la funzione generica `compute_score` ha un default più permissivo (5.0 s) per evitare sovrapenalizzazioni fuori dai grafici.
- memory_ref: 100 MB (memoria “accettabile”)

Pesi (importanza relativa): w_cost = 0.7, w_time = 0.2, w_mem = 0.1 (costo > tempo > memoria).

Snippet (semplificato):

```python
from math import log, exp

def compute_score(cost, violations, time_s, memory_mb, cost_ref, time_ref=0.1, memory_ref=100.0,
              w_cost=0.7, w_time=0.2, w_mem=0.1, lambda_penalty=10.0, mapping="exp"):
   # Rinormalizza i pesi se la memoria non è disponibile
   if memory_mb is None:
      total = w_cost + w_time
      w_cost, w_time, w_mem = w_cost/total, w_time/total, 0.0

   cost_eff = cost + lambda_penalty * float(violations)
   L = w_cost * (cost_eff / cost_ref) + w_time * log(1 + time_s / time_ref)
   if memory_mb is not None:
      L += w_mem * log(1 + memory_mb / memory_ref)

   return 100.0 * exp(-L) if mapping == "exp" else 100.0 / (1.0 + L)
```

Nel codice del tool, la funzione `evaluate_solution` è un wrapper che prepara i dati (notare che la memoria misurata internamente è in KB e viene convertita in MB per lo scoring) e invoca `compute_score` con i riferimenti sopra. Per le immagini/tabella l’app usa in genere time_ref=0.1 s e memory_ref=100 MB, mentre il default “generico” di `compute_score` è 5.0 s: i risultati visualizzati sono coerenti perché i riferimenti sono esplicitati nelle chiamate.

#### 📦 Riquadro teoria e riferimenti (scoring)

> Perché MAUT e perché così?
>
> - Multi-Attribute Utility Theory (MAUT) consente di aggregare attributi eterogenei (costo, tempo, memoria) in modo coerente con preferenze e trade-off; l’additività è appropriata se gli attributi sono indipendenti in utilità (Keeney & Raiffa, 1976).
> - La mappatura esponenziale negativa, score = 100·exp(−L), garantisce monotonia e comprime code alte (robusta a outlier su tempo/memoria); l’alternativa 100/(1+L) è più lineare ma meno “outlier-robust”.
> - I log su tempo/memoria modellano rendimenti decrescenti su scale molto asimmetriche (passare da 0.05→0.1 s “pesa” più che da 5→5.05 s).
> - I pesi (0.7, 0.2, 0.1) riflettono una priorità didattica: costo ≫ tempo > memoria. Sono normalizzati automaticamente se la memoria non è disponibile.
> - Penalità di violazione (λ ≈ 10.0) converte “violazioni” in unità di costo; 1 violazione vale circa 10 unità di costo nel baseline. Aumentare λ enfatizza il rispetto dei vincoli.
>
> Proprietà utili
>
> - Monotonicità: aumentando cost/violations/time/memory, L cresce e lo score decresce.
> - Bordi: L→0 implica score→100; L grande implica score→0 ma mai negativo.
> - Coerenza tra vista tabellare e grafico: entrambi invocano la stessa formula e gli stessi riferimenti.
>
> Sensibilità/come tarare
>
> - cost_ref: usare il Greedy della stessa istanza stabilizza i confronti; in alternativa, un costo noto/atteso.
> - time_ref/memory_ref: scegliere soglie “accettabili” (0.1 s; 100 MB) secondo il contesto hardware/didattico.
> - w_cost/w_time/w_mem: calibrare in base alle priorità del corso/tesi; mantenere somma=1.
>
> Riferimenti
>
> - Keeney, R.L., Raiffa, H. (1976). Decisions with Multiple Objectives: Preferences and Value Tradeoffs. Wiley.
> - Fishburn, P.C. (1970). Utility Theory for Decision Making. Wiley.

---

## 📄 Licenza

Progetto rilasciato con licenza MIT — vedi il file [LICENSE](LICENSE).
