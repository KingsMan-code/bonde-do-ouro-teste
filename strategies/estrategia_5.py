"""
Estratégia 5: Take Profit Escalonado + Médias Móveis
- Entrada: Golden Cross
- Saída: Take Profit escalonado (50% em +1%, 30% em +2%, 20% até death cross)
"""
import pandas as pd
import numpy as np
from services.marketdata import add_technical_indicators

def simular_estrategia_5(symbol: str, percentual_entrada: float, interval: str, df_candles: pd.DataFrame) -> dict:
    """
    Simula a estratégia com take profit escalonado
    
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
        "estrategia": "take_profit_escalonado",
        "results_by_combo": results_by_combo,
        "winner": {"combo": winner['combo'], "retorno_pct": winner['retorno_pct']}
    }

def _simulate_single_combo(df: pd.DataFrame, ma_short: int, ma_long: int, 
                          percentual_entrada: float, symbol: str, interval: str) -> dict:
    """
    Simula uma única combinação de MAs com take profit escalonado
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
    position_size = 0.0  # Tamanho restante da posição
    total_return = 0.0
    trades = []
    current_trade = None
    
    # Adiciona colunas para logging
    df_with_indicators['signal_buy_price'] = np.nan
    df_with_indicators['signal_sell_price'] = np.nan
    df_with_indicators['trade_pnl_pct'] = np.nan
    df_with_indicators['combo'] = f"{ma_short}x{ma_long}"
    df_with_indicators['estrategia'] = "take_profit_escalonado"
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
                position_size = 1.0  # 100% da posição inicial
                
                current_trade = {
                    'entry_price': entry_price,
                    'partial_exits': [],
                    'total_return': 0.0
                }
                
                # Marca no DataFrame
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('signal_buy_price')] = entry_price
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('reason')] = "golden_cross"
        
        # Sinal de saída
        elif position_open and current_trade:
            sell_signal = False
            sell_reason = ""
            sell_percentage = 0.0
            
            # TP1: +1% - vende 50% da posição
            if (current_price >= entry_price * 1.01 and 
                position_size >= 0.5 and 
                not any(exit['reason'] == 'tp_1pct' for exit in current_trade['partial_exits'])):
                sell_signal = True
                sell_reason = "tp_1pct"
                sell_percentage = 0.5
            
            # TP2: +2% - vende 30% da posição original
            elif (current_price >= entry_price * 1.02 and 
                  position_size >= 0.3 and 
                  not any(exit['reason'] == 'tp_2pct' for exit in current_trade['partial_exits'])):
                sell_signal = True
                sell_reason = "tp_2pct"
                sell_percentage = 0.3
            
            # Death Cross: vende o restante da posição (20%)
            elif (prev_row['ma_short'] >= prev_row['ma_long'] and 
                  current_row['ma_short'] < current_row['ma_long'] and
                  position_size > 0):
                sell_signal = True
                sell_reason = "death_cross"
                sell_percentage = position_size  # Vende tudo que resta
            
            if sell_signal:
                # Calcula o retorno desta saída parcial
                partial_return = (current_price - entry_price) / entry_price
                weighted_return = partial_return * sell_percentage
                current_trade['total_return'] += weighted_return
                
                # Registra a saída parcial
                current_trade['partial_exits'].append({
                    'price': current_price,
                    'percentage': sell_percentage,
                    'return_pct': partial_return * 100,
                    'reason': sell_reason
                })
                
                # Atualiza o tamanho da posição
                position_size -= sell_percentage
                
                # Marca no DataFrame
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('signal_sell_price')] = current_price
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('trade_pnl_pct')] = partial_return * 100
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('reason')] = sell_reason
                
                # Se vendeu tudo ou foi death cross, fecha a posição
                if position_size <= 0.01 or sell_reason == "death_cross":
                    total_return += current_trade['total_return'] * percentual_entrada
                    
                    trades.append({
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'return_pct': current_trade['total_return'] * 100,
                        'reason': 'escalonado',
                        'partial_exits': current_trade['partial_exits']
                    })
                    
                    position_open = False
                    entry_price = 0.0
                    position_size = 0.0
                    current_trade = None
    
    # Calcula estatísticas
    num_trades = len(trades)
    win_rate = 0.0
    
    if num_trades > 0:
        winning_trades = sum(1 for trade in trades if trade['return_pct'] > 0)
        win_rate = (winning_trades / num_trades) * 100
    
    return {
        "combo": f"{ma_short}x{ma_long}",
        "retorno_pct": total_return * 100,
        "trades": num_trades,
        "win_rate_pct": win_rate,
        "_df_log": df_with_indicators  # Para salvar no CSV
    }

