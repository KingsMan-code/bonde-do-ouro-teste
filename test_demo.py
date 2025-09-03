"""
Demonstração do Sistema de Backtesting com dados simulados
(Para contornar restrições geográficas da API da Binance)
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategies.conservadora import simular_conservadora
from strategies.arriscada import simular_arriscada

# ===== PARÂMETROS FIXOS =====
SYMBOL = "BTCUSDT"
ALOCACAO_POR_ENTRADA = 1.0  # 100% da banca
TIMEFRAME = "1h"
LIMIT_CANDLES = 1000

def generate_sample_data(num_candles=1000, start_price=45000):
    """
    Gera dados simulados de candles para demonstração
    """
    print(f"Gerando {num_candles} candles simuladas para demonstração...")
    
    # Gera timestamps
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=num_candles)
    timestamps = pd.date_range(start=start_time, end=end_time, freq='H')[:num_candles]
    
    # Simula movimento de preços com tendência e volatilidade
    np.random.seed(42)  # Para resultados reproduzíveis
    
    prices = []
    current_price = start_price
    
    for i in range(num_candles):
        # Adiciona tendência e ruído
        trend = 0.0001 * np.sin(i / 100)  # Tendência cíclica
        noise = np.random.normal(0, 0.02)  # Volatilidade
        
        change = trend + noise
        current_price = current_price * (1 + change)
        
        # Gera OHLC para a candle
        high = current_price * (1 + abs(np.random.normal(0, 0.01)))
        low = current_price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = current_price * (1 + np.random.normal(0, 0.005))
        close_price = current_price
        
        prices.append({
            'open': open_price,
            'high': max(open_price, high, close_price),
            'low': min(open_price, low, close_price),
            'close': close_price
        })
    
    # Cria DataFrame
    df = pd.DataFrame({
        'open_time': timestamps,
        'close_time': timestamps + timedelta(hours=1),
        'open': [p['open'] for p in prices],
        'high': [p['high'] for p in prices],
        'low': [p['low'] for p in prices],
        'close': [p['close'] for p in prices],
        'volume': np.random.uniform(100, 1000, num_candles)
    })
    
    return df

def main():
    """
    Função principal de demonstração
    """
    print("=" * 60)
    print("DEMONSTRAÇÃO - SISTEMA DE BACKTESTING")
    print("=" * 60)
    print("⚠️  Usando dados simulados para demonstração")
    
    try:
        # 1. Simular saldo
        print("\\n1. Simulando consulta de saldo...")
        saldo_simulado = 1000.0  # $1000 USDT
        print(f"✓ Saldo USDT simulado: {saldo_simulado:.2f}")
        
        # 2. Gerar dados simulados
        print(f"\\n2. Gerando dados simulados para {SYMBOL} ({TIMEFRAME})...")
        df_candles = generate_sample_data(LIMIT_CANDLES)
        print(f"✓ {len(df_candles)} candles geradas")
        print(f"✓ Período: {df_candles['open_time'].iloc[0]} até {df_candles['open_time'].iloc[-1]}")
        
        # 3. Criar pasta de logs com timestamp
        timestamp = datetime.now().strftime("%m-%d-%Y-%H-%M")
        log_dir = f"logs/demo_{timestamp}"
        os.makedirs(log_dir, exist_ok=True)
        print(f"✓ Pasta de logs criada: {log_dir}")
        
        # 4. Executar Estratégia Conservadora
        print("\\n3. Executando Estratégia Conservadora...")
        resultado_conservadora = simular_conservadora(
            SYMBOL, ALOCACAO_POR_ENTRADA, TIMEFRAME, df_candles
        )
        
        # 5. Executar Estratégia Arriscada
        print("\\n4. Executando Estratégia Arriscada...")
        resultado_arriscada = simular_arriscada(
            SYMBOL, ALOCACAO_POR_ENTRADA, TIMEFRAME, df_candles
        )
        
        # 6. Gerar logs CSV
        print("\\n5. Gerando logs CSV...")
        _save_strategy_logs(resultado_conservadora, log_dir, SYMBOL, TIMEFRAME)
        _save_strategy_logs(resultado_arriscada, log_dir, SYMBOL, TIMEFRAME)
        
        # 7. Imprimir relatório no console
        print("\\n6. Relatório de Resultados:")
        _print_strategy_report(resultado_conservadora, SYMBOL, TIMEFRAME)
        _print_strategy_report(resultado_arriscada, SYMBOL, TIMEFRAME)
        
        print(f"\\n✓ Demonstração concluída! Logs salvos em: {log_dir}")
        print("\\n📊 O sistema está funcionando corretamente!")
        print("💡 Para usar com dados reais, execute main.py com acesso à API da Binance")
        
    except Exception as e:
        print(f"❌ Erro durante a demonstração: {e}")
        import traceback
        traceback.print_exc()

def _save_strategy_logs(resultado_estrategia: dict, log_dir: str, symbol: str, interval: str):
    """
    Salva os logs CSV de uma estratégia
    """
    estrategia_nome = resultado_estrategia['estrategia']
    
    # Combina todos os DataFrames de log das combinações
    all_logs = []
    
    for combo_result in resultado_estrategia['results_by_combo']:
        if '_df_log' in combo_result:
            df_log = combo_result['_df_log']
            all_logs.append(df_log)
    
    if all_logs:
        # Concatena todos os logs
        combined_df = pd.concat(all_logs, ignore_index=True)
        
        # Salva o CSV
        filename = f"{estrategia_nome}_{symbol}_{interval}.csv"
        filepath = os.path.join(log_dir, filename)
        combined_df.to_csv(filepath, index=False)
        print(f"✓ Log salvo: {filename}")

def _print_strategy_report(resultado_estrategia: dict, symbol: str, interval: str):
    """
    Imprime o relatório formatado de uma estratégia
    """
    estrategia_nome = resultado_estrategia['estrategia'].upper()
    results = resultado_estrategia['results_by_combo']
    winner = resultado_estrategia['winner']
    
    print(f"\\n=== Estratégia: {estrategia_nome} ({symbol} / {interval}) ===")
    print(f"{'combo':<8} {'retorno%':<10} {'trades':<8} {'win_rate%':<10}")
    print("-" * 40)
    
    # Ordena por retorno (desc), depois win_rate (desc), depois trades (desc)
    sorted_results = sorted(
        results, 
        key=lambda x: (x['retorno_pct'], x['win_rate_pct'], x['trades']), 
        reverse=True
    )
    
    for result in sorted_results:
        combo = result['combo']
        retorno = result['retorno_pct']
        trades = result['trades']
        win_rate = result['win_rate_pct']
        
        # Formata o retorno com sinal
        retorno_str = f"{retorno:+.2f}%"
        win_rate_str = f"{win_rate:.2f}" if trades > 0 else "0.00"
        
        print(f"{combo:<8} {retorno_str:<10} {trades:<8} {win_rate_str:<10}")
    
    # Destaca a vencedora
    winner_retorno = f"{winner['retorno_pct']:+.2f}%"
    print(f"\\nVencedora ({estrategia_nome.title()}): {winner['combo']}  |  {winner_retorno}")

if __name__ == "__main__":
    main()

