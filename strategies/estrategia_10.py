"""
Estratégia 10: Otimização de Parâmetros + Médias Móveis
- Entrada: Golden Cross com range expandido de combinações
- Saída: TP fixo +1% ou Death Cross (o que acontecer primeiro)
- Testa um range muito maior de combinações para encontrar ótimos
"""
import pandas as pd
import numpy as np
from services.marketdata import add_technical_indicators

def simular_estrategia_10(symbol: str, percentual_entrada: float, interval: str, df_candles: pd.DataFrame) -> dict:
    """
    Simula a estratégia com otimização de parâmetros (range expandido)
    
    Args:
        symbol (str): Par de trading
        percentual_entrada (float): Percentual da banca para cada entrada (ex: 1.0 = 100%)
        interval (str): Timeframe
        df_candles (pd.DataFrame): DataFrame com dados OHLCV
    
    Returns:
        dict: Resultados da simulação
    """
    # Range expandido de combinações para otimização
    ma_combinations = []
    
    # EMA curta: 5-15 períodos
    # SMA longa: 20-100 períodos
    for ma_short in range(5, 16):  # 5 a 15
        for ma_long in [20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]:
            if ma_short < ma_long:  # Garante que a curta seja menor que a longa
                ma_combinations.append((ma_short, ma_long))
    
    # Adiciona algumas combinações clássicas
    classic_combinations = [
        (7, 21), (8, 21), (9, 27), (10, 30), (12, 26), 
        (20, 50), (21, 55), (24, 72)
    ]
    
    for combo in classic_combinations:
        if combo not in ma_combinations:
            ma_combinations.append(combo)
    
    results_by_combo = []
    
    print(f"Testando {len(ma_combinations)} combinações de parâmetros...")
    
    for i, (ma_short, ma_long) in enumerate(ma_combinations):
        if i % 20 == 0:  # Progress update
            print(f"Progresso: {i}/{len(ma_combinations)} combinações testadas")
        
        result = _simulate_single_combo(
            df_candles, ma_short, ma_long, percentual_entrada, symbol, interval
        )
        results_by_combo.append(result)
    
    # Encontra a combinação vencedora
    winner = max(results_by_combo, key=lambda x: (x['retorno_pct'], x['win_rate_pct'], x['trades']))
    
    # Mostra top 10 combinações
    top_10 = sorted(results_by_combo, key=lambda x: (x['retorno_pct'], x['win_rate_pct'], x['trades']), reverse=True)[:10]
    
    print("\\nTop 10 combinações encontradas:")
    for i, combo in enumerate(top_10, 1):
        print(f"{i:2d}. {combo['combo']}: {combo['retorno_pct']:+.2f}% ({combo['trades']} trades, {combo['win_rate_pct']:.1f}% win rate)")
    
    return {
        "estrategia": "otimizacao_parametros",
        "results_by_combo": results_by_combo,
        "winner": {"combo": winner['combo'], "retorno_pct": winner['retorno_pct']},
        "top_10": top_10
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
    
    # Adiciona colunas para logging (apenas para a combinação vencedora)
    df_with_indicators['signal_buy_price'] = np.nan
    df_with_indicators['signal_sell_price'] = np.nan
    df_with_indicators['trade_pnl_pct'] = np.nan
    df_with_indicators['combo'] = f"{ma_short}x{ma_long}"
    df_with_indicators['estrategia'] = "otimizacao_parametros"
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
    
    return {
        "combo": f"{ma_short}x{ma_long}",
        "retorno_pct": total_return * 100,
        "trades": num_trades,
        "win_rate_pct": win_rate,
        "_df_log": df_with_indicators  # Para salvar no CSV
    }

