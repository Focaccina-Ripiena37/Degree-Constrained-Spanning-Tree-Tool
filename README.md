# 🌳 DCST Tool – Degree-Constrained Spanning Tree App

**DCST Tool** è un’applicazione con interfaccia grafica sviluppata in Python per affrontare il problema dell’**albero di copertura di peso minimo con vincolo di grado (DCMST)**, un problema noto in Ricerca Operativa per la sua complessità (NP-Hard).  
L'app è stata progettata per fini didattici e di ricerca, con particolare attenzione alla **modularità**, **usabilità** e **visualizzazione dei risultati**.

````markdown
TESTO DEL PROBLEMA:
Dato un grafo pesato, non completo, e un nodo r, si cerca lo spanning tree di costo minimo di radice r tale
che ogni nodo non abbia piú di k figli.
````

## 🧠 Obiettivo

Risolvere il problema mettendo a paragone tre diverse strategie:

- ⚙️ **Greedy** – costruttivo, rapido ma sub-ottimo
- 🔁 **Local Search** – migliora la soluzione greedy, correggendo le violazioni
- 🔥 **Simulated Annealing** – metaeuristica per esplorazione avanzata dello spazio delle soluzioni


## 🖼️ Funzionalitá

Il programma dispone di una semplice interfaccia grafica (GUI) realizzata in Tkinter che consente di:
- Impostare i parametri per la ricerca
- Visualizzazione grafica dell’avanzamento
- Barra di stato e log testuale in tempo reale

Le altre funzionalitá base sono:
- Esportazione automatica di file su desktop

![{0D7070D1-43B6-43CF-A4B7-F56DF2413700}](https://github.com/user-attachments/assets/6b290961-4e20-473c-9a97-4db2cc74fa66)

---

## 🐍 Come eseguire il programma

### 🪟 WINDOWS 10/11

#### 📌 1. Clona la repository

```bash
git clone https://github.com/Focaccina-Ripiena37/Degree-Constrained-Spanning-Tree-Tool.git
```

⚠️Necessita avere [Git per Windows](https://git-scm.com/downloads/win) installato

O scarica la repo da questa pagina come .zip

#### 📌 2. Installa le dipendenze

Esegui il file `install_dependencies.cmd` come **Amministratore**

#### 📌 3. Avvia l’app

Doppio clic sul file `play.vbs` 

...oppure...

Spostati nella main directory da terminale ed esegui: 

```bash
python run.py
```

### 🍎 MAC OS

  #### 📌 1. Dai i permessi di esecuzione allo script `setup_dcst.command` per installare le dipendenze (da Terminale) con:
  
  ```bash
  chmod +x setup_dcst.command
  ```
  
  #### 📌 2. Fai doppio clic oppure esegui dal Finder o da Terminale il file `setup_dcst.command`
  
  #### 📌 3. Avvia l’app
  
  Spostati dentro la directory di progetto da terminale ed esegui
  
  ```bash
  python3 run.py
  ```

---

## 📁 Output

Al termine dell’ottimizzazione, i risultati verranno salvati automaticamente in:

```bash
~/Desktop/Plot
```

Troverai:

* Grafi iniziali
* Alberi ottimizzati
* Tabella di confronto
* Grafico dei punteggi

---

## 🧪 Tecnologie usate

* 🐍 Python 3.11
* 🎨 Tkinter (GUI)
* 📈 Matplotlib, NetworkX, PIL

## 📦 Supporto

- **Windows 10/11** ✅completo
- **MacOS** ⚠️parziale
- **Linux** ⚠️non testato

---

## ❓ Problemi noti

- Su MacOS i bottoni della UI non hanno colore
- Su MacOS a volte i grafici dei grafi grandi non vengono stampati completamente

---

## 📬 Contatti

Per problemi, suggerimenti o contributi: apri una [Issue](../../issues).

🚀 *Progetto sviluppato per il corso di Ricerca Operativa – A.A. 2024/2025*

