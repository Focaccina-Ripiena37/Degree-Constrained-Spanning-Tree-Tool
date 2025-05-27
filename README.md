# 🌳 DCST Tool – Degree-Constrained Spanning Tree App

**DCST Tool** è un’applicazione con interfaccia grafica sviluppata in Python per affrontare il problema dell’**albero di copertura con vincolo di grado (DCMST)**, un problema noto in Ricerca Operativa per la sua complessità (NP-Hard).  
L'app è stata progettata per fini didattici e di ricerca, con particolare attenzione alla **modularità**, **usabilità** e **visualizzazione dei risultati**.

````markdown
TESTO DEL PROBLEMA:
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


## 🖼️ Interfaccia grafica (Tkinter)

- Impostazione parametri: nodi per istanze (piccola, media, grande), probabilità `p`, `max_children`, penalità
- Visualizzazione grafica dell’avanzamento
- Barra di stato e log testuale in tempo reale
- Esportazione automatica di file su desktop

![{0D7070D1-43B6-43CF-A4B7-F56DF2413700}](https://github.com/user-attachments/assets/6b290961-4e20-473c-9a97-4db2cc74fa66)


## 🐍 Esecuzione da codice sorgente Windows

#### 📌 1. Clona il repository
```bash
git clone https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.git
cd Degree-Constrained-Spanning-Tree-Tool
```

#### 📌 2. Installa le dipendenze

Esegui il file `install_dependencies.cmd` come **Amministratore**

#### 📌 4. Avvia l’app

Spostati nella main directory e esegui: 

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

* Grafi iniziali (PNG)
* Alberi ottimizzati (Greedy, LS, SA)
* Tabella di confronto (PNG)
* Grafico dei punteggi (PNG)

---

## 🧪 Tecnologie usate

* 🐍 Python 3.11
* 🎨 Tkinter (GUI)
* 📈 Matplotlib, NetworkX, PIL

## 📦 Supporto

- **Windows 10/11**

---

## 📬 Contatti

Per problemi, suggerimenti o contributi: apri una [Issue](../../issues).

🚀 *Progetto sviluppato per il corso di Ricerca Operativa – A.A. 2024/2025*

