"""
Estratégia 9: Bollinger Bands + Médias Móveis
- Entrada: Golden Cross + Preço próximo à banda inferior (contexto de volatilidade)
- Saída: TP fixo +1%, Death Cross ou preço próximo à banda superior
"""
import pandas as pd
import numpy as np
from services.marketdata import add_technical_indicators

def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0):
    """
    Calcula as Bollinger Bands
    """
    close = df['close']
    
    # Média móvel simples
    sma = close.rolling(window=period, min_periods=period).mean()
    
    # Desvio padrão
    std = close.rolling(window=period, min_periods=period).std()
    
    # Bandas
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return upper_band, sma, lower_band

def simular_estrategia_9(symbol: str, percentual_entrada: float, interval: str, df_candles: pd.DataFrame) -> dict:
    """
    Simula a estratégia com Bollinger Bands
    
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
        "estrategia": "bollinger_bands",
        "results_by_combo": results_by_combo,
        "winner": {"combo": winner['combo'], "retorno_pct": winner['retorno_pct']}
    }

def _simulate_single_combo(df: pd.DataFrame, ma_short: int, ma_long: int, 
                          percentual_entrada: float, symbol: str, interval: str) -> dict:
    """
    Simula uma única combinação de MAs com Bollinger Bands
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
    
    # Adiciona Bollinger Bands
    upper_band, middle_band, lower_band = calculate_bollinger_bands(df_with_indicators, 20, 2.0)
    df_with_indicators['bb_upper'] = upper_band
    df_with_indicators['bb_middle'] = middle_band
    df_with_indicators['bb_lower'] = lower_band
    
    # Calcula posição relativa do preço nas bandas (0 = banda inferior, 1 = banda superior)
    df_with_indicators['bb_position'] = (df_with_indicators['close'] - df_with_indicators['bb_lower']) / (df_with_indicators['bb_upper'] - df_with_indicators['bb_lower'])
    
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
    df_with_indicators['estrategia'] = "bollinger_bands"
    df_with_indicators['reason'] = ""
    
    for i in range(1, len(df_with_indicators)):
        current_row = df_with_indicators.iloc[i]
        prev_row = df_with_indicators.iloc[i-1]
        
        current_price = current_row['close']
        
        # Verifica se há dados suficientes para as MAs e Bollinger Bands
        if (pd.isna(current_row['ma_short']) or pd.isna(current_row['ma_long']) or 
            pd.isna(current_row['bb_upper']) or pd.isna(current_row['bb_lower']) or
            pd.isna(current_row['bb_position'])):
            continue
        
        # Sinal de entrada: Golden Cross + Contexto Bollinger Bands
        if not position_open:
            # Golden Cross: MA curta cruza para cima da MA longa
            golden_cross = (prev_row['ma_short'] <= prev_row['ma_long'] and 
                           current_row['ma_short'] > current_row['ma_long'])
            
            # Contexto Bollinger: preço na metade inferior das bandas (posição < 0.5)
            # Isso indica que o preço não está em sobrecompra
            bb_context = current_row['bb_position'] < 0.5
            
            # Filtro adicional: preço não muito próximo da banda inferior (evita knife catching)
            not_oversold = current_row['bb_position'] > 0.1
            
            if golden_cross and bb_context and not_oversold:
                position_open = True
                entry_price = current_price
                
                # Marca no DataFrame
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('signal_buy_price')] = entry_price
                df_with_indicators.iloc[i, df_with_indicators.columns.get_loc('reason')] = "golden_cross_bb_context"
        
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
            
            # Saída adicional: preço próximo à banda superior (sobrecompra)
            elif current_row['bb_position'] > 0.9:
                sell_signal = True
                sell_reason = "bb_overbought"
            
            if sell_signal:
                # Calcula o retorno da operação
                trade_return = (current_price - entry_price) / entry_price
                total_return += trade_return * percentual_entrada
                
                trades.append({
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'return_pct': trade_return * 100,
                    'reason': sell_reason,
                    'entry_bb_position': df_with_indicators.iloc[df_with_indicators[df_with_indicators['signal_buy_price'] == entry_price].index[0]]['bb_position'] if len(df_with_indicators[df_with_indicators['signal_buy_price'] == entry_price]) > 0 else np.nan,
                    'exit_bb_position': current_row['bb_position']
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
    
    return {
        "combo": f"{ma_short}x{ma_long}",
        "retorno_pct": total_return * 100,
        "trades": num_trades,
        "win_rate_pct": win_rate,
        "_df_log": df_with_indicators  # Para salvar no CSV
    }

