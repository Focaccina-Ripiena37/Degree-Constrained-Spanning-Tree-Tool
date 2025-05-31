#!/bin/bash

echo "================================"
echo " DCST Tool - Setup Dependencies "
echo "================================"

# 1. Controlla se Python 3 è installato
if ! command -v python3 &> /dev/null
then
    echo "Python 3 non trovato. Avvio installazione con Homebrew..."
    # Installa Homebrew se manca
    if ! command -v brew &> /dev/null
    then
        echo "Homebrew non trovato. Installazione in corso..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    # Installa Python 3
    brew install python@3.10
else
    echo "Python 3 è già installato."
fi

# 2. Assicurati che 'python3' funzioni
if ! python3 --version &> /dev/null
then
    echo "Errore: Python 3 non è stato installato correttamente."
    exit 1
fi

# 3. Aggiorna pip
echo "Aggiornamento pip..."
python3 -m pip install --upgrade pip

# 4. Installa le dipendenze (solo per l'utente corrente)
echo "Installazione dipendenze..."
python3 -m pip install --user pandas tqdm tabulate numpy matplotlib networkx psutil pillow memory_profiler scipy

echo "================================"
echo " Tutto pronto!"
echo " Ora puoi eseguire:"
echo
echo "     python3 run.py"
echo
echo "================================"

read -n 1 -s -r -p "Premi un tasto per chiudere la finestra..."
exit 0
