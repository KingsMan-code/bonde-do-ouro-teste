"""
Cliente da Binance para conectar com a API usando as credenciais do .env
"""
import os
from dotenv import load_dotenv
from binance.client import Client

def create_binance_client():
    """
    Cria e retorna um cliente da Binance usando as credenciais do arquivo .env
    
    Returns:
        Client: Cliente da Binance configurado
    """
    # Carrega as variáveis de ambiente do arquivo .env
    load_dotenv()
    
    # Obtém as credenciais das variáveis de ambiente
    api_key = os.getenv("KEY_BINANCE")
    api_secret = os.getenv("SECRET_BINANCE")
    
    if not api_key or not api_secret:
        raise ValueError("Credenciais da Binance não encontradas no arquivo .env")
    
    # Cria e retorna o cliente
    client = Client(api_key, api_secret, testnet=False)
    
    return client

