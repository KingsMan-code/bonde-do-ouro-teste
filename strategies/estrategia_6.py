"""
Estratégia 6: Gestão de Posição Adaptativa + Médias Móveis
- Entrada: Golden Cross com tamanho de posição baseado na volatilidade
- Saída: TP fixo +1% ou Death Cross (o que acontecer primeiro)
- Tamanho da posição varia inversamente com a volatilidade (ATR)
"""
import pandas as pd
import numpy as np
from services.marketdata import add_technical_indicators

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calcula o Average True Range (ATR)
    """
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close)
    tr3 = abs(low - close)
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period, min_periods=period).mean()
    
    return atr

def simular_estrategia_6(symbol: str, percentual_entrada: float, interval: str, df_candles: pd.DataFrame) -> dict:
    """
    Simula a estratégia com gestão de posição adaptativa
    
    Args:
        symbol (str): Par de trading
        percentual_entrada (float): Percentual da banca para cada entrada (ex: 1.0 = 100%)
        interval (str): Timeframe
        df_candles (pd.DataFrame): DataFrame com dados OHLCV
    
    Returns:
        dict: Resultados da simulação
    """
    # Combinações de MAs para testar
    ma_combinations = [
        (7, 21), (7, 25), (8, 21), (9, 27), (10, 30), 
        (12, 26), (20, 50), (21, 55), (24, 72)
    ]
    
    results_by_combo = []
    
    for ma_short, ma_long in ma_combinations:
        result = _simulate_single_combo(
            df_candles, ma_short, ma_long, percentual_entrada, symbol, interval
        )
        results_by_combo.append(result)
    
    # Encontra a combinação vencedora
    winner = max(results_by_combo, key=lambda x: (x['retorno_pct'], x['win_rate_pct'], x['trades']))
    
    return {
        "estrategia": "gestao_posicao_adaptativa",
        "results_by_combo": results_by_combo,
        "winner": {"combo": winner['combo'], "retorno_pct": winner['retorno_pct']}
    }

def _simulate_single_combo(df: pd.DataFrame, ma_short: int, ma_long: int, 
                          percentual_entrada: float, symbol: str, interval: str) -> dict:
    """
    Simula uma única combinação de MAs com gestão de posição adaptativa
    """
    if df.empty:
        return {
            "combo": f"{ma_short}x{ma_long}",
            "retorno_pct": 0.0,
            "trades": 0,
            "win_rate_pct": 0.0
        }
    
    # Adiciona indicadores técnicos
    df_with_indicators = add_technical_indicators(df.copy(), ma_short, ma_long)
    
    # Adiciona ATR para gestão de posição
    df_with_indicators['atr_14'] = calculate_atr(df_with_indicators, 14)
    df_with_indicators['atr_ma_50'] = df_with_indicators['atr_14'].rolling(window=50, min_periods=50).mean()
    
    # Inicializa variáveis de controle
    position_open = False
    entry_price = 0.0
    position_size = 0.0
    total_return = 0.0
    trades = []
    
    # Adiciona colunas para logging
    df_with_indicators['signal_buy_price'] = np.nan
    df_with_indicators['signal_sell_price'] = np.nan
    df_with_indicators['trade_pnl_pct'] = np.nan
    df_with_indicators['combo'] = f"{ma_short}x{ma_long}"
    df_with_indicators['estrategia'] = "gestao_posicao_adaptativa"
    df_with_indicators['reason'] = ""
    df_with_indicators['position_size'] = np.nan
    
    for i in range(1, len(df_with_indicators)):
        current_row = df_with_indicators.iloc[i]
        prev_row = df_with_indicators.iloc[i-1]
        
        current_price = current_row['close']
        
        # Verifica se há dados suficientes para as MAs e ATR
        if (pd.isna(current_row['ma_short']) or pd.isna(current_row['ma_long']) or 
            pd.isna(current_row['atr_14']) or pd.isna(current_row['atr_ma_50'])):
            continue
        
        # Sinal de entrada: Golden Cross
        if not position_open:
            # Golden Cross: MA curta cruza para cima da MA longa
            if (prev_row['ma_short'] <= prev_row['ma_long'] and 
                current_row['ma_short'] > current_row['ma_long']):
                
                # Calcula tamanho da posição baseado na volatilidade
                # Menor volatilidade = maior posição, maior volatilidade = menor posição
                atr_ratio = current_row['atr_14'] / current_row['atr_ma_50']
                
                if atr_ratio <= 0.8:  # Baixa volatilidade
                    position_size = 1.0  # 100% da banca
                elif atr_ratio <= 1.2:  # Volatilidade normal
                    position_size = 0.75  # 75% da banca
                elif atr_ratio <= 1.5:  # Alta volatilidade
                    position_size = 0.5   # 50% da banca
                else:  # Volatilidade muito alta
                    position_size = 0.25  # 25% da banca
                
                position_open = True
                entry_price = current_price
                
                # Marca no DataFrame
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('signal_buy_price')] = entry_price
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('reason')] = "golden_cross"
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('position_size')] = position_size
        
        # Sinal de saída
        elif position_open:
            sell_signal = False
            sell_reason = ""
            
            # TP: +1%
            if current_price >= entry_price * 1.01:
                sell_signal = True
                sell_reason = "tp_1pct"
            
            # Death Cross: MA curta cruza para baixo da MA longa
            elif (prev_row['ma_short'] >= prev_row['ma_long'] and 
                  current_row['ma_short'] < current_row['ma_long']):
                sell_signal = True
                sell_reason = "death_cross"
            
            if sell_signal:
                # Calcula o retorno da operação considerando o tamanho da posição
                trade_return = (current_price - entry_price) / entry_price
                weighted_return = trade_return * position_size
                total_return += weighted_return * percentual_entrada
                
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'return_pct': trade_return * 100,
                    'position_size': position_size,
                    'weighted_return_pct': weighted_return * 100,
                    'reason': sell_reason
                })
                
                # Marca no DataFrame
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('signal_sell_price')] = current_price
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('trade_pnl_pct')] = weighted_return * 100
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('reason')] = sell_reason
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('position_size')] = position_size
                
                position_open = False
                entry_price = 0.0
                position_size = 0.0
    
    # Calcula estatísticas
    num_trades = len(trades)
    win_rate = 0.0
    
    if num_trades > 0:
        winning_trades = sum(1 for trade in trades if trade['weighted_return_pct'] > 0)
        win_rate = (winning_trades / num_trades) * 100
    
    return {
        "combo": f"{ma_short}x{ma_long}",
        "retorno_pct": total_return * 100,
        "trades": num_trades,
        "win_rate_pct": win_rate,
        "_df_log": df_with_indicators  # Para salvar no CSV
    }

