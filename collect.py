#!/usr/bin/env python3
"""
Rio Rise Rewards Collector - Versão Windows
Coleta recompensas diárias para múltiplos UIDs
"""

import requests
import json
import time
import uuid
import sys
import os
from datetime import datetime
from pathlib import Path

# ============================================================================
# CONFIGURAÇÃO - EDITE AQUI SE NECESSÁRIO
# ============================================================================

# Use barras normais (/) ou Path() - Python cuida do resto!
UIDS_FILE = "meus_uids.txt"
OUTPUT_FILE = "rewards_results.json"  # Arquivo de saída

BASE_URL = "https://hub-api.aghanim.com/hub/v1/websites/riorise.shop"
WEBSITE = "riorise.shop"

# ============================================================================
# FUNÇÕES
# ============================================================================

def print_header(text):
    """Imprime um cabeçalho formatado"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_success(text):
    """Imprime mensagem de sucesso"""
    print(f"✓ {text}")

def print_error(text):
    """Imprime mensagem de erro"""
    print(f"✗ {text}")

def print_warning(text):
    """Imprime mensagem de aviso"""
    print(f"~ {text}")

def print_info(text):
    """Imprime mensagem informativa"""
    print(f"ℹ {text}")

def load_uids(filename):
    """Carrega UIDs do arquivo"""
    try:
        # Usar Path para compatibilidade com Windows
        filepath = Path(filename)
        
        if not filepath.exists():
            print_error(f"Arquivo '{filename}' não encontrado!")
            print_info(f"Crie um arquivo '{filename}' no mesmo diretório com um UID por linha")
            print_info(f"Diretório atual: {Path.cwd()}")
            sys.exit(1)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            uids = [line.strip().lstrip('#') for line in f if line.strip()]
        
        if not uids:
            print_error(f"Arquivo '{filename}' está vazio!")
            sys.exit(1)
        
        return uids
    except Exception as e:
        print_error(f"Erro ao ler arquivo: {e}")
        sys.exit(1)

def login_and_get_token(uid):
    """Faz login com o UID e retorna o token JWT"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9',
        'Origin': f'https://{WEBSITE}',
        'Referer': f'https://{WEBSITE}/pt/daily-rewards',
        'Content-Type': 'application/json',
    }
    
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/authorize_user_id",
            json={"user_id": uid},
            headers=headers,
            timeout=15,
            verify=True
        )
        
        if resp.status_code != 200:
            return None, None
        
        data = resp.json()
        token = data.get('token')
        csrf_token = str(uuid.uuid4())
        
        return token, csrf_token
    except Exception as e:
        return None, None

def get_daily_rewards_status(token, csrf_token):
    """Obtém o status das recompensas diárias"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Authorization': f'Bearer {token}',
        'x-csrf-token': csrf_token,
        'Accept': 'application/json, text/plain, */*',
        'Origin': f'https://{WEBSITE}',
        'Referer': f'https://{WEBSITE}/pt/daily-rewards',
    }
    
    try:
        resp = requests.get(
            f"{BASE_URL}/daily_rewards",
            headers=headers,
            timeout=15,
            verify=True
        )
        
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        return None

def claim_daily_reward(token, csrf_token, day):
    """Reivindica a recompensa do dia especificado"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Authorization': f'Bearer {token}',
        'x-csrf-token': csrf_token,
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/plain, */*',
        'Origin': f'https://{WEBSITE}',
        'Referer': f'https://{WEBSITE}/pt/daily-rewards',
    }
    
    try:
        resp = requests.post(
            f"{BASE_URL}/daily_rewards/claim/day/{day}",
            headers=headers,
            timeout=15,
            verify=True
        )
        
        try:
            return resp.status_code, resp.json()
        except:
            return resp.status_code, {}
    except Exception as e:
        return None, None

def collect_rewards(uids):
    """Coleta recompensas para todos os UIDs"""
    results = []
    success_count = 0
    no_available_count = 0
    error_count = 0
    
    print_header(f"Iniciando coleta de {len(uids)} UIDs")
    print_info(f"Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    
    for i, uid in enumerate(uids, 1):
        # Mostrar progresso
        progress = f"[{i:3d}/{len(uids)}]"
        print(f"{progress} UID: {uid[:20]}...", end=' ', flush=True)
        
        result = {
            'uid': uid,
            'status': 'error',
            'message': '',
            'day': None,
            'reward': None,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            # Fazer login e obter token
            token, csrf_token = login_and_get_token(uid)
            
            if not token:
                result['message'] = 'Falha no login - UID inválido'
                print_error("Login falhou")
                error_count += 1
                results.append(result)
                time.sleep(0.5)
                continue
            
            # Obter status das recompensas
            dr_data = get_daily_rewards_status(token, csrf_token)
            
            if not dr_data:
                result['message'] = 'Falha ao obter status das recompensas'
                print_error("Status falhou")
                error_count += 1
                results.append(result)
                time.sleep(0.5)
                continue
            
            # Encontrar o dia disponível para reivindicar
            available_day = None
            reward_items = []
            all_states = []
            
            for dr in dr_data.get('daily_rewards', []):
                state = dr.get('state', '')
                all_states.append(f"D{dr['day_number']}:{state}")
                if state == 'available':
                    available_day = dr['day_number']
                    reward_items = dr.get('items', [])
            
            if available_day is None:
                result['status'] = 'no_available'
                result['message'] = f'Nenhum dia disponível. Estados: {", ".join(all_states)}'
                print_warning("Sem disponível")
                no_available_count += 1
                results.append(result)
                time.sleep(0.5)
                continue
            
            # Reivindicar a recompensa
            status_code, claim_result = claim_daily_reward(token, csrf_token, available_day)
            
            if status_code == 200:
                reward_desc = ', '.join([f"{item.get('quantity')}x {item.get('name')}" for item in reward_items])
                result['status'] = 'success'
                result['day'] = available_day
                result['reward'] = reward_desc
                result['message'] = f'Dia {available_day}: {reward_desc}'
                print_success(f"Dia {available_day}: {reward_desc}")
                success_count += 1
            else:
                result['message'] = f'Falha ao reivindicar: {status_code}'
                print_error(f"Falha: {status_code}")
                error_count += 1
        
        except Exception as e:
            result['message'] = f'Erro: {str(e)}'
            print_error(f"Erro: {e}")
            error_count += 1
        
        results.append(result)
        time.sleep(0.5)
    
    return results, success_count, no_available_count, error_count

def save_results(results, filename):
    """Salva resultados em arquivo JSON"""
    try:
        filepath = Path(filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print_error(f"Erro ao salvar resultados: {e}")
        return False

def print_summary(total, success, no_available, errors):
    """Imprime resumo final"""
    print_header("RESUMO FINAL")
    
    print(f"Total de UIDs processados: {total}")
    print(f"  ✓ Recompensas coletadas:     {success:3d} ({success*100//total if total > 0 else 0}%)")
    print(f"  ~ Sem recompensa disponível: {no_available:3d} ({no_available*100//total if total > 0 else 0}%)")
    print(f"  ✗ Erros (UID inválido etc):  {errors:3d} ({errors*100//total if total > 0 else 0}%)")
    
    print(f"\nResultados salvos em: {Path(OUTPUT_FILE).absolute()}")
    print(f"Hora de conclusão: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    try:
        print_header("Rio Rise Rewards Collector - Windows")
        
        # Mostrar diretório atual
        print_info(f"Diretório atual: {Path.cwd()}")
        print_info(f"Procurando arquivo: {UIDS_FILE}\n")
        
        # Carregar UIDs
        print_info(f"Carregando UIDs de '{UIDS_FILE}'...")
        uids = load_uids(UIDS_FILE)
        print_success(f"{len(uids)} UIDs carregados\n")
        
        # Coletar recompensas
        results, success, no_available, errors = collect_rewards(uids)
        
        # Salvar resultados
        print_info(f"\nSalvando resultados em '{OUTPUT_FILE}'...")
        if save_results(results, OUTPUT_FILE):
            print_success("Resultados salvos com sucesso")
        
        # Imprimir resumo
        print_summary(len(uids), success, no_available, errors)
        
        # Aguardar antes de fechar
        # print_info("\nPressione ENTER para fechar...")
        # input()
        
    except KeyboardInterrupt:
        print_error("\n\nOperação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print_error(f"Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        print_info("\nPressione ENTER para fechar...")
        input()
        sys.exit(1)
