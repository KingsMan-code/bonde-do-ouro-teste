"""
Estratégia Conservadora
- Entrada: Golden Cross (MA curta cruza para cima da MA longa)
- Saída: TP fixo +1% ou Death Cross (o que acontecer primeiro)
"""
import pandas as pd
import numpy as np
from services.marketdata import add_technical_indicators

def simular_conservadora(symbol: str, percentual_entrada: float, interval: str, df_candles: pd.DataFrame) -> dict:
    """
    Simula a estratégia conservadora
    
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
        (7, 21), (7, 25), (8, 21), (9, 27), (10, 30)
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
        "estrategia": "conservadora",
        "results_by_combo": results_by_combo,
        "winner": {"combo": winner['combo'], "retorno_pct": winner['retorno_pct']}
    }

def _simulate_single_combo(df: pd.DataFrame, ma_short: int, ma_long: int, 
                          percentual_entrada: float, symbol: str, interval: str) -> dict:
    """
    Simula uma única combinação de MAs
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
    
    # Inicializa variáveis de controle
    position_open = False
    entry_price = 0.0
    total_return = 0.0
    trades = []
    
    # Adiciona colunas para logging
    df_with_indicators['signal_buy_price'] = np.nan
    df_with_indicators['signal_sell_price'] = np.nan
    df_with_indicators['trade_pnl_pct'] = np.nan
    df_with_indicators['combo'] = f"{ma_short}x{ma_long}"
    df_with_indicators['estrategia'] = "conservadora"
    df_with_indicators['reason'] = ""
    
    for i in range(1, len(df_with_indicators)):
        current_row = df_with_indicators.iloc[i]
        prev_row = df_with_indicators.iloc[i-1]
        
        current_price = current_row['close']
        
        # Verifica se há dados suficientes para as MAs
        if pd.isna(current_row['ma_short']) or pd.isna(current_row['ma_long']):
            continue
        
        # Sinal de entrada: Golden Cross
        if not position_open:
            # Golden Cross: MA curta cruza para cima da MA longa
            if (prev_row['ma_short'] <= prev_row['ma_long'] and 
                current_row['ma_short'] > current_row['ma_long']):
                
                position_open = True
                entry_price = current_price
                
                # Marca no DataFrame
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('signal_buy_price')] = entry_price
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('reason')] = "golden_cross"
        
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
                # Calcula o retorno da operação
                trade_return = (current_price - entry_price) / entry_price
                total_return += trade_return * percentual_entrada
                
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'return_pct': trade_return * 100,
                    'reason': sell_reason
                })
                
                # Marca no DataFrame
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('signal_sell_price')] = current_price
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('trade_pnl_pct')] = trade_return * 100
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('reason')] = sell_reason
                
                position_open = False
                entry_price = 0.0
    
    # Calcula estatísticas
    num_trades = len(trades)
    win_rate = 0.0
    
    if num_trades > 0:
        winning_trades = sum(1 for trade in trades if trade['return_pct'] > 0)
        win_rate = (winning_trades / num_trades) * 100
    
    # Salva dados para log (será usado pelo main.py)
    df_with_indicators._combo_data = {
        'symbol': symbol,
        'interval': interval,
        'ma_short': ma_short,
        'ma_long': ma_long
    }
    
    return {
        "combo": f"{ma_short}x{ma_long}",
        "retorno_pct": total_return * 100,
        "trades": num_trades,
        "win_rate_pct": win_rate,
        "_df_log": df_with_indicators  # Para salvar no CSV
    }

