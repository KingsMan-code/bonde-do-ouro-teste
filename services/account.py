"""
Serviço para consultar informações da conta (somente leitura)
"""
from binance.client import Client

def get_account_balance(client: Client, asset: str = "USDT"):
    """
    Consulta o saldo de um ativo específico na conta
    
    Args:
        client (Client): Cliente da Binance
        asset (str): Ativo a consultar (padrão: USDT)
    
    Returns:
        dict: Informações do saldo do ativo
    """
    try:
        # Obtém informações da conta
        account_info = client.get_account()
        
        # Procura pelo ativo específico
        for balance in account_info['balances']:
            if balance['asset'] == asset:
                return {
                    'asset': asset,
                    'free': float(balance['free']),
                    'locked': float(balance['locked']),
                    'total': float(balance['free']) + float(balance['locked'])
                }
        
        # Se não encontrou o ativo, retorna saldo zero
        return {
            'asset': asset,
            'free': 0.0,
            'locked': 0.0,
            'total': 0.0
        }
        
    except Exception as e:
        print(f"Erro ao consultar saldo: {e}")
        return {
            'asset': asset,
            'free': 0.0,
            'locked': 0.0,
            'total': 0.0,
            'error': str(e)
        }

def get_all_balances(client: Client):
    """
    Consulta todos os saldos da conta (apenas ativos com saldo > 0)
    
    Args:
        client (Client): Cliente da Binance
    
    Returns:
        list: Lista com todos os saldos não-zero
    """
    try:
        account_info = client.get_account()
        balances = []
        
        for balance in account_info['balances']:
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                balances.append({
                    'asset': balance['asset'],
                    'free': free,
                    'locked': locked,
                    'total': total
                })
        
        return balances
        
    except Exception as e:
        print(f"Erro ao consultar saldos: {e}")
        return []

