"""
Serviço para buscar dados de mercado (candles/klines)
"""
import pandas as pd
from binance.client import Client
from datetime import datetime

def get_historical_klines(client: Client, symbol: str, interval: str, limit: int = 1000):
    """
    Busca as últimas candles históricas de um par
    
    Args:
        client (Client): Cliente da Binance
        symbol (str): Par de trading (ex: BTCUSDT)
        interval (str): Timeframe (ex: 1h, 4h, 1d)
        limit (int): Número de candles (máximo 1000)
    
    Returns:
        pd.DataFrame: DataFrame com os dados normalizados
    """
    try:
        # Busca os dados da Binance
        klines = client.get_historical_klines(symbol, interval, limit=limit)
        
        if not klines:
            print(f"Nenhum dado encontrado para {symbol} no timeframe {interval}")
            return pd.DataFrame()
        
        # Cria DataFrame com as colunas corretas
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Converte timestamps para datetime (sem timezone)
        df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
        df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')
        
        # Converte colunas numéricas
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                          'quote_asset_volume', 'number_of_trades',
                          'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume']
        
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove colunas desnecessárias e mantém apenas as principais
        df = df[['open_time', 'close_time', 'open', 'high', 'low', 'close', 'volume']].copy()
        
        # Remove timezone se existir
        if df['open_time'].dt.tz is not None:
            df['open_time'] = df['open_time'].dt.tz_localize(None)
        if df['close_time'].dt.tz is not None:
            df['close_time'] = df['close_time'].dt.tz_localize(None)
        
        # Ordena por tempo
        df = df.sort_values('open_time').reset_index(drop=True)
        
        print(f"Dados carregados: {len(df)} candles para {symbol} ({interval})")
        print(f"Período: {df['open_time'].iloc[0]} até {df['open_time'].iloc[-1]}")
        
        return df
        
    except Exception as e:
        print(f"Erro ao buscar dados de mercado: {e}")
        return pd.DataFrame()

def add_technical_indicators(df: pd.DataFrame, ma_short: int, ma_long: int):
    """
    Adiciona indicadores técnicos ao DataFrame
    
    Args:
        df (pd.DataFrame): DataFrame com dados OHLCV
        ma_short (int): Período da média móvel curta
        ma_long (int): Período da média móvel longa
    
    Returns:
        pd.DataFrame: DataFrame com indicadores adicionados
    """
    if df.empty:
        return df
    
    df = df.copy()
    
    # Calcula médias móveis exponenciais
    df[f'ema_{ma_short}'] = df['close'].ewm(span=ma_short).mean()
    df[f'ema_{ma_long}'] = df['close'].ewm(span=ma_long).mean()
    
    # Adiciona colunas padronizadas para as estratégias
    df['ma_short'] = df[f'ema_{ma_short}']
    df['ma_long'] = df[f'ema_{ma_long}']
    
    return df

