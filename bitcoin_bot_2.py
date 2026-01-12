import os
import requests
import concurrent.futures
import re
import time
from bit import Key

# --- CONFIGURAÇÕES ---
# O script buscará estas variáveis nos Secrets do GitHub
MASTER_KEY = os.getenv("MASTER_KEY")
CUSTODY_ADDRESS = os.getenv("CUSTODY_ADDRESS")

# Configuração de Varredura (Equilibrada para estabilidade)
WORKERS = 20
PAGES_PER_WORKER = 500 
TOTAL_PAGES = WORKERS * PAGES_PER_WORKER

STATE_FILE = "bot_state.txt"
BASE_URL = "https://keys.lol/bitcoin/"

def check_balance_and_rescue(pk_hex):
    """Verifica saldo e transfere se houver."""
    try:
        key = Key.from_hex(pk_hex)
        # Log de monitoramento (Endereço e Saldo)
        balance = key.get_balance('btc')
        print(f"Verificando: {key.address} | Saldo: {balance} BTC")
        
        if float(balance) > 0:
            print(f"!!! SUCESSO: {balance} BTC ENCONTRADOS EM {key.address} !!!")
            if CUSTODY_ADDRESS:
                tx_hash = key.send([(CUSTODY_ADDRESS, float(balance), 'btc')])
                print(f"Transferência realizada: {tx_hash}")
            return True
    except:
        pass
    return False

def process_page(page_num, session):
    """Extrai chaves de uma página e as verifica."""
    try:
        response = session.get(f"{BASE_URL}{page_num}", timeout=10)
        if response.status_code == 200:
            keys = re.findall(r'[a-fA-F0-9]{64}', response.text)
            for pk in set(keys):
                check_balance_and_rescue(pk)
    except:
        pass

def worker_task(start_page):
    with requests.Session() as session:
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        for i in range(PAGES_PER_WORKER):
            process_page(start_page + i, session)

def run():
    print("--- Iniciando Bitcoin Scan v1.0 ---")
    
    # Carregar estado anterior
    start_page = 1
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                start_page = int(f.read().strip())
        except:
            pass

    print(f"Iniciando na página: {start_page}")
    print(f"Meta do ciclo: {TOTAL_PAGES} páginas")

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as executor:
        executor.map(worker_task, [start_page + (i * PAGES_PER_WORKER) for i in range(WORKERS)])

    # Salvar próximo estado
    with open(STATE_FILE, "w") as f:
        f.write(str(start_page + TOTAL_PAGES))
    
    print(f"Ciclo finalizado. Próxima execução iniciará na página {start_page + TOTAL_PAGES}")

if __name__ == "__main__":
    run()
