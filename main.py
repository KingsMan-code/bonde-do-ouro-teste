"""
Sistema de Backtesting de Estratégias de Trading
Orquestra o fluxo completo: saldo -> dados -> estratégias -> logs -> relatórios
"""
import os
import pandas as pd
from datetime import datetime
from services.binance_client import create_binance_client
from services.account import get_account_balance
from services.marketdata import get_historical_klines
from strategies.conservadora import simular_conservadora

# ===== PARÂMETROS FIXOS (fácil de alterar) =====
SYMBOL = "BTCUSDT"
ALOCACAO_POR_ENTRADA = 1.0  # 100% da banca
TIMEFRAME = "1h"
LIMIT_CANDLES = 1000

def main():
    """
    Função principal que orquestra todo o fluxo
    """
    print("=" * 60)
    print("SISTEMA DE BACKTESTING - ESTRATÉGIAS DE TRADING")
    print("=" * 60)
    
    try:
        # 1. Carregar .env e instanciar o Client
        print("\\n1. Conectando com a Binance...")
        client = create_binance_client()
        print("✓ Cliente da Binance criado com sucesso")
        
        # 2. Consultar saldo
        print("\\n2. Consultando saldo da conta...")
        saldo_usdt = get_account_balance(client, "USDT")
        print(f"✓ Saldo USDT: {saldo_usdt['total']:.2f}")
        
        if 'error' in saldo_usdt:
            print(f"⚠️  Aviso: {saldo_usdt['error']}")
        
        # 3. Buscar últimas 1000 candles
        print(f"\\n3. Buscando dados de mercado para {SYMBOL} ({TIMEFRAME})...")
        df_candles = get_historical_klines(client, SYMBOL, TIMEFRAME, LIMIT_CANDLES)
        
        if df_candles.empty:
            print("❌ Erro: Não foi possível obter dados de mercado")
            return
        
        print(f"✓ {len(df_candles)} candles carregadas")
        
        # 4. Criar pasta de logs com timestamp
        timestamp = datetime.now().strftime("%m-%d-%Y-%H-%M")
        log_dir = f"logs/{timestamp}"
        os.makedirs(log_dir, exist_ok=True)
        print(f"✓ Pasta de logs criada: {log_dir}")
        
        # 5. Executar Estratégia Conservadora
        print("\\n4. Executando Estratégia Conservadora...")
        resultado_conservadora = simular_conservadora(
            SYMBOL, ALOCACAO_POR_ENTRADA, TIMEFRAME, df_candles
        )
        
        # 6. Gerar logs CSV
        print("\\n5. Gerando logs CSV...")
        _save_strategy_logs(resultado_conservadora, log_dir, SYMBOL, TIMEFRAME)
        
        # 7. Imprimir relatório no console
        print("\\n6. Relatório de Resultados:")
        _print_strategy_report(resultado_conservadora, SYMBOL, TIMEFRAME)
        
        print(f"\\n✓ Execução concluída! Logs salvos em: {log_dir}")
        
    except Exception as e:
        print(f"❌ Erro durante a execução: {e}")
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

