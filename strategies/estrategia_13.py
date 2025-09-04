"""
Estratégia 13: Conservadora BB + MAs (entradas e saídas otimizadas)
- Entrada: Golden Cross (EMA curta cruza para cima da SMA longa)
           + confirmação por Bandas de Bollinger (força acima da banda média OU squeeze)
- Saída (ordem de prioridade):
  1) TP adaptativo ao tocar/fechar na Banda Superior,
  2) Trailing ao perder a Banda Média,
  3) Stop por ATR (dinâmico),
  4) Death Cross (fallback).
"""
import pandas as pd
import numpy as np
from services.marketdata import add_technical_indicators

# Parâmetros padrão de volatilidade/BB/ATR para a estratégia 13
_BB_WINDOW       = 20
_BB_STD          = 2.0
_ATR_WINDOW      = 14
_SQUEEZE_WINDOW  = 100
_SQUEEZE_QUANT   = 0.20   # 20% menor largura histórica = squeeze
_ATR_STOP_MULT   = 1.5    # 1.5x ATR abaixo do preço de entrada


def simular_estrategia_13(symbol: str, percentual_entrada: float, interval: str, df_candles: pd.DataFrame) -> dict:
    """
    Simula a estratégia 13 (Conservadora com BB + MAs)
    
    Args:
        symbol (str): Par de trading
        percentual_entrada (float): Percentual da banca para cada entrada (ex: 1.0 = 100%)
        interval (str): Timeframe
        df_candles (pd.DataFrame): DataFrame com dados OHLCV
    
    Returns:
        dict: Resultados da simulação
    """
    # Mantém a ideia de varrer combinações de MAs como na estratégia 0
    ma_combinations = [
        (7, 21), (7, 25), (8, 21), (9, 27), (10, 30), 
        (12, 26), (20, 50), (21, 55), (24, 72)
    ]
    
    results_by_combo = []
    for ma_short, ma_long in ma_combinations:
        result = _simulate_single_combo_13(
            df_candles=df_candles,
            ma_short=ma_short,
            ma_long=ma_long,
            percentual_entrada=percentual_entrada,
            symbol=symbol,
            interval=interval
        )
        results_by_combo.append(result)
    
    winner = max(results_by_combo, key=lambda x: (x['retorno_pct'], x['win_rate_pct'], x['trades']))
    return {
        "estrategia": "conservadora_bb_ma",
        "results_by_combo": results_by_combo,
        "winner": {"combo": winner['combo'], "retorno_pct": winner['retorno_pct']}
    }


def _compute_bb_atr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula Bandas de Bollinger e ATR no DF (sem depender de serviços externos).
    Requer colunas: ['close','high','low'].
    """
    df = df.copy()

    # Bandas de Bollinger
    mb = df['close'].rolling(_BB_WINDOW, min_periods=_BB_WINDOW).mean()
    sd = df['close'].rolling(_BB_WINDOW, min_periods=_BB_WINDOW).std(ddof=0)
    ub = mb + _BB_STD * sd
    lb = mb - _BB_STD * sd
    df['bb_mid'] = mb
    df['bb_upper'] = ub
    df['bb_lower'] = lb

    # %B e largura
    width = (ub - lb)
    df['bb_percent_b'] = (df['close'] - lb) / width.replace(0, np.nan)
    df['bb_bandwidth'] = (ub - lb) / mb.replace(0, np.nan)

    # ATR (True Range)
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift(1)).abs()
    lc = (df['low']  - df['close'].shift(1)).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    df['atr'] = tr.rolling(_ATR_WINDOW, min_periods=_ATR_WINDOW).mean()

    # Limiar de squeeze (rolling quantile)
    # Se rolling.quantile não estiver disponível/performático, caímos num fallback simples
    try:
        df['bb_bw_q'] = df['bb_bandwidth'].rolling(_SQUEEZE_WINDOW, min_periods=_SQUEEZE_WINDOW)\
                                          .quantile(_SQUEEZE_QUANT)
    except Exception:
        bw_mean = df['bb_bandwidth'].rolling(_SQUEEZE_WINDOW, min_periods=_SQUEEZE_WINDOW).mean()
        bw_std  = df['bb_bandwidth'].rolling(_SQUEEZE_WINDOW, min_periods=_SQUEEZE_WINDOW).std(ddof=0)
        df['bb_bw_q'] = (bw_mean - bw_std).clip(lower=0)

    return df


def _simulate_single_combo_13(df_candles: pd.DataFrame, ma_short: int, ma_long: int, 
                              percentual_entrada: float, symbol: str, interval: str) -> dict:
    """
    Simula uma única combinação de MAs com filtro/saídas baseados em Bandas de Bollinger e ATR.
    """
    if df_candles.empty:
        return {
            "combo": f"{ma_short}x{ma_long}",
            "retorno_pct": 0.0,
            "trades": 0,
            "win_rate_pct": 0.0
        }
    
    # 1) Calcula MAs conforme sua função padrão (esperado: cria 'ma_short' e 'ma_long')
    df = add_technical_indicators(df_candles.copy(), ma_short, ma_long)

    # 2) Adiciona BB/ATR
    df = _compute_bb_atr(df)

    # 3) Inicialização de estado/log
    position_open = False
    entry_price   = 0.0
    entry_idx     = None
    total_return  = 0.0
    trades        = []

    df['signal_buy_price']  = np.nan
    df['signal_sell_price'] = np.nan
    df['trade_pnl_pct']     = np.nan
    df['combo']             = f"{ma_short}x{ma_long}"
    df['estrategia']        = "conservadora_bb_ma"
    df['reason']            = ""

    # 4) Loop de barras
    for i in range(1, len(df)):
        row   = df.iloc[i]
        prev  = df.iloc[i-1]
        price = row['close']

        # Indicadores necessários válidos?
        needed = ['ma_short', 'ma_long', 'bb_mid', 'bb_upper', 'bb_lower', 'atr', 'bb_percent_b', 'bb_bandwidth', 'bb_bw_q']
        if any(pd.isna(row.get(c, np.nan)) for c in needed):
            continue

        # ---------------- ENTRADA ----------------
        if not position_open:
            # Golden Cross (EMA curta cruza acima da SMA longa)
            golden_cross = (prev['ma_short'] <= prev['ma_long']) and (row['ma_short'] > row['ma_long'])

            # Confirmação por BB:
            # (a) força: fechar acima da banda média e %B > 0.5
            bb_force_ok = (price > row['bb_mid']) and (row['bb_percent_b'] > 0.5)
            # (b) squeeze: largura atual <= quantil baixo histórico
            squeeze_ok  = (row['bb_bandwidth'] <= row['bb_bw_q'])

            if golden_cross and (bb_force_ok or squeeze_ok):
                position_open = True
                entry_price   = price
                entry_idx     = i

                df.iat[i, df.columns.get_loc('signal_buy_price')] = entry_price
                df.iat[i, df.columns.get_loc('reason')] = "golden_cross_bb_confirm"

        # ----------------  SAÍDAS  ----------------
        else:
            sell_signal = False
            sell_reason = ""

            # 1) TP adaptativo: toque/fechamento na banda superior
            if price >= row['bb_upper']:
                sell_signal = True
                sell_reason = "tp_bb_upper"

            # 2) Trailing: perde a banda média (fecha abaixo)
            elif price < row['bb_mid']:
                sell_signal = True
                sell_reason = "trail_mid_break"

            # 3) Stop por ATR (dinâmico ao risco)
            elif price <= entry_price - _ATR_STOP_MULT * row['atr']:
                sell_signal = True
                sell_reason = "atr_stop"

            # 4) Death Cross (fallback)
            elif (prev['ma_short'] >= prev['ma_long']) and (row['ma_short'] < row['ma_long']):
                sell_signal = True
                sell_reason = "death_cross"

            if sell_signal:
                trade_return = (price - entry_price) / entry_price
                total_return += trade_return * percentual_entrada

                trades.append({
                    'entry_index': int(entry_idx) if entry_idx is not None else None,
                    'exit_index': int(i),
                    'entry_price': float(entry_price),
                    'exit_price': float(price),
                    'return_pct': float(trade_return * 100.0),
                    'reason': sell_reason
                })

                df.iat[i, df.columns.get_loc('signal_sell_price')] = price
                df.iat[i, df.columns.get_loc('trade_pnl_pct')]     = trade_return * 100.0
                df.iat[i, df.columns.get_loc('reason')]            = sell_reason

                position_open = False
                entry_price   = 0.0
                entry_idx     = None
    
    # 5) Métricas
    num_trades = len(trades)
    win_rate   = 0.0
    if num_trades > 0:
        wins = sum(1 for t in trades if t['return_pct'] > 0)
        win_rate = (wins / num_trades) * 100.0

    # 6) Retorno no padrão esperado
    return {
        "combo": f"{ma_short}x{ma_long}",
        "retorno_pct": total_return * 100.0,
        "trades": num_trades,
        "win_rate_pct": win_rate,
        "_df_log": df  # Para salvar no CSV/Excel, tal como no código 0
    }
