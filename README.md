Perfetto Lorenzo, ecco una versione **più completa del `README.md`**, ottimizzata per la homepage della tua repo:

* ✅ Compatta ma informativa
* 📦 Con istruzioni per l’eseguibile **e** per l’avvio via sorgente
* 🛠 Include installazione dipendenze e info pratiche

---

# 🌳 DCST Tool – Degree-Constrained Spanning Tree App

**DCST Tool** è un’applicazione con interfaccia grafica sviluppata in Python per affrontare il problema dell’**albero di copertura con vincolo di grado (DCST)**, un problema noto in Ricerca Operativa per la sua complessità (NP-Hard).  
L'app è stata progettata per fini didattici e di ricerca, con particolare attenzione alla **modularità**, **usabilità** e **visualizzazione dei risultati**.

````markdown
**TESTO DEL PROBLEMA: **
Dato un grafo pesato, non completo, e un nodo r, si cerca lo spanning tree di costo minimo di radice r tale
che ogni nodo non abbia piú di k figli.
````

---

## 🧠 Obiettivo

Trovare alberi di copertura su grafi con vincolo di grado massimo su ogni nodo.  
L'app implementa tre algoritmi:

- ⚙️ **Greedy** – costruttivo, rapido ma sub-ottimo
- 🔁 **Local Search** – migliora la soluzione greedy, correggendo le violazioni
- 🔥 **Simulated Annealing** – metaeuristica per esplorazione avanzata dello spazio delle soluzioni

---

## 🖼️ Interfaccia grafica (Tkinter)

- Impostazione parametri: nodi per istanze (piccola, media, grande), probabilità `p`, `max_children`, penalità
- Visualizzazione grafica dell’avanzamento
- Barra di stato e log testuale in tempo reale
- Esportazione automatica su desktop di:
  - grafi (`grafo_iniziale_...`)
  - alberi ottimizzati
  - tabelle comparative

---

## 📦 Esecuzione

### ✅ Modalità 1: Eseguibile standalone

Vai nella [sezione Releases](../../releases) e scarica il file per il tuo sistema:

- 🪟 `DCST_Tool_Windows.exe`
- 🍎 ~~`DCST_Tool_macOS`~~
- 🐧 ~~`DCST_Tool_Linux`~~

Non richiede Python né librerie esterne.

---

### 🐍 Modalità 2: Esecuzione da codice sorgente

#### 📌 1. Clona il repository
```bash
git clone https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.git
cd Degree-Constrained-Spanning-Tree-Tool


#### 📌 2. Crea ambiente virtuale (opzionale ma consigliato)

```bash
python -m venv venv
source venv/bin/activate      # su Linux/macOS
venv\Scripts\activate.bat     # su Windows
```

#### 📌 3. Installa le dipendenze

```bash
pip install matplotlib pandas networkx pillow
```

#### 📌 4. Avvia l’app

```bash
python run.py
```

---

## 📁 Output

Al termine dell’ottimizzazione, i risultati verranno salvati automaticamente in:

```bash
~/Desktop/Plot
```

Troverai:

* Grafi iniziali
* Alberi ottimizzati (Greedy, LS, SA)
* Tabella di confronto (PNG)

---

## 📚 Background teorico

Il problema DCST estende l'MST imponendo limiti al numero di figli per ogni nodo (`max_children`).
È stato dimostrato **NP-Hard anche per k=2**.
La nostra app impiega euristiche sequenziali, perfezionate con una metaeuristica di tipo Simulated Annealing per evitare ottimi locali.

---

## 🧪 Tecnologie usate

* 🐍 Python 3.11
* 🎨 Tkinter (GUI)
* 📈 Matplotlib, NetworkX, PIL
* ⚙️ PyInstaller per le build multipiattaforma

---

## 📦 Rilascio binari

Trovi gli eseguibili già compilati nella sezione [Releases](../../releases).
Supporto: Windows, macOS, Linux.

---

## 📬 Contatti

Per problemi, suggerimenti o contributi: apri una [Issue](../../issues).

---

🚀 *Progetto sviluppato per il corso di Ricerca Operativa – A.A. 2024/2025*

```
