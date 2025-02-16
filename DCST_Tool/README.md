# DCST Tool

## Descrizione
Questo programma fornisce un'interfaccia grafica per la generazione e l'analisi di alberi di copertura con vincoli di grado. Utilizza diversi algoritmi per ottimizzare la costruzione degli alberi e visualizzarne i risultati.

## Requisiti
Il programma è scritto in **Python** e richiede diverse librerie esterne per funzionare correttamente.

### Dipendenze richieste
Le seguenti librerie devono essere installate:
- `networkx`
- `matplotlib`
- `pandas`
- `tabulate`
- `numpy`
- `tkinter`
- `tqdm`
- `Pillow`

## Installazione delle dipendenze
Puoi installare tutte le dipendenze necessarie eseguendo il file `install_dependencies.cmd` su Windows.

In alternativa, puoi installarle manualmente con il seguente comando:
```sh
pip install networkx matplotlib pandas tabulate numpy tqdm Pillow
```

## Esecuzione del programma
Per avviare il programma:
1. Assicurati di aver installato tutte le dipendenze.
2. Esegui il seguente comando nel terminale:
   ```sh
   python Main-Q2.5.py
   ```

## Funzionamento
L'interfaccia consente di:
- Impostare il numero di nodi per istanze piccole, medie e grandi.
- Avviare il calcolo degli alberi di copertura con diversi algoritmi.
- Visualizzare e salvare i risultati generati in formato immagine.

## Salvataggio dei risultati
I file immagine generati dal programma vengono salvati automaticamente nella cartella **Plot** situata sul **Desktop** dell'utente. 
I risultati includono:
- Grafici dei grafi generati.
- Alberi di copertura ottenuti tramite diversi algoritmi.
- Tabelle con i risultati delle analisi, salvate come immagini.

## Gestione degli errori
Il programma gestisce e riporta eventuali errori che possono verificarsi durante l'esecuzione. Di seguito, alcune delle situazioni più comuni:

- **Errore nella generazione del grafo:** se il programma non riesce a creare un grafo connesso dopo numerosi tentativi, viene mostrato un messaggio di errore e l'istanza non verrà processata.
- **Errore nella costruzione dello spanning tree:** se non è possibile costruire un albero di copertura che rispetti i vincoli imposti, l'istanza verrà ignorata e non sarà presente alcuna immagine nella cartella **Plot**.
- **Errore nei calcoli:** se durante il calcolo si verificano problemi, il programma li segnalerà tramite una finestra di errore o un messaggio nel terminale.

Se un'istanza specifica non può essere processata, ma le altre sì, allora nella cartella **Plot** saranno presenti solo le immagini relative alle istanze che hanno avuto successo. Nessuna immagine sarà creata per quelle problematiche.

## Supporto
Per segnalazioni o richieste di aiuto, aprire un'issue su GitHub o contattare l'autore.

