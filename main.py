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

# ===== PARÂMETROS FIXOS (fácil de alterar) =====
SYMBOL = "BTCUSDT"
ALOCACAO_POR_ENTRADA = 1.0  # 100% da banca
TIMEFRAME = "1h"
LIMIT_CANDLES = 1000

# ===== ESTRATÉGIAS DISPONÍVEIS =====
ESTRATEGIAS = {
    0: {
        'nome': 'Conservadora Original',
        'modulo': 'strategies.estrategia_0',
        'funcao': 'simular_estrategia_0'
    },
    1: {
        'nome': 'Filtros de Tendência + Médias Móveis',
        'modulo': 'strategies.estrategia_1',
        'funcao': 'simular_estrategia_1'
    },
    2: {
        'nome': 'Confirmação de Volume + Médias Móveis',
        'modulo': 'strategies.estrategia_2',
        'funcao': 'simular_estrategia_2'
    },
    3: {
        'nome': 'Filtro de Volatilidade (ATR) + Médias Móveis',
        'modulo': 'strategies.estrategia_3',
        'funcao': 'simular_estrategia_3'
    },
    4: {
        'nome': 'Stop Loss Dinâmico + Médias Móveis',
        'modulo': 'strategies.estrategia_4',
        'funcao': 'simular_estrategia_4'
    },
    5: {
        'nome': 'Take Profit Escalonado + Médias Móveis',
        'modulo': 'strategies.estrategia_5',
        'funcao': 'simular_estrategia_5'
    },
    6: {
        'nome': 'Gestão de Posição Adaptativa + Médias Móveis',
        'modulo': 'strategies.estrategia_6',
        'funcao': 'simular_estrategia_6'
    },
    7: {
        'nome': 'RSI como Filtro + Médias Móveis',
        'modulo': 'strategies.estrategia_7',
        'funcao': 'simular_estrategia_7'
    },
    8: {
        'nome': 'MACD Confirmação + Médias Móveis',
        'modulo': 'strategies.estrategia_8',
        'funcao': 'simular_estrategia_8'
    },
    9: {
        'nome': 'Bollinger Bands + Médias Móveis',
        'modulo': 'strategies.estrategia_9',
        'funcao': 'simular_estrategia_9'
    },
    10: {
        'nome': 'Otimização de Parâmetros + Médias Móveis',
        'modulo': 'strategies.estrategia_10',
        'funcao': 'simular_estrategia_10'
    },
    11: {
        'nome': 'Multi-Timeframe + Médias Móveis',
        'modulo': 'strategies.estrategia_11',
        'funcao': 'simular_estrategia_11'
    },
    12: {
        'nome': 'SMA 200 + Volume + ATR + Médias Móveis (Combo)',
        'modulo': 'strategies.estrategia_12',
        'funcao': 'simular_estrategia_12'
    },
    13: {
        'nome': 'Bollinger Bands + Médias Móveis (Combo)',
        'modulo': 'strategies.estrategia_13',
        'funcao': 'simular_estrategia_13'
    }
}

def escolher_estrategia():
    """
    Permite ao usuário escolher qual estratégia executar
    """
    print("\\n" + "=" * 80)
    print("ESCOLHA A ESTRATÉGIA PARA BACKTESTING")
    print("=" * 80)
    
    for num, info in ESTRATEGIAS.items():
        print(f"{num:2d} - {info['nome']}")
    
    print("=" * 80)
    
    while True:
        try:
            escolha = int(input("\\nDigite o número da estratégia (0-12): "))
            if escolha in ESTRATEGIAS:
                return escolha
            else:
                print("❌ Número inválido! Escolha entre 0 e 12.")
        except ValueError:
            print("❌ Por favor, digite apenas números!")

def importar_estrategia(numero_estrategia):
    """
    Importa dinamicamente a estratégia escolhida
    """
    try:
        estrategia_info = ESTRATEGIAS[numero_estrategia]
        modulo = __import__(estrategia_info['modulo'], fromlist=[estrategia_info['funcao']])
        funcao_estrategia = getattr(modulo, estrategia_info['funcao'])
        return funcao_estrategia, estrategia_info['nome']
    except ImportError as e:
        print(f"❌ Erro ao importar estratégia {numero_estrategia}: {e}")
        return None, None

def main():
    """
    Função principal que orquestra todo o fluxo
    """
    print("=" * 60)
    print("SISTEMA DE BACKTESTING - ESTRATÉGIAS DE TRADING")
    print("=" * 60)
    
    try:
        # 0. Escolher estratégia
        numero_estrategia = escolher_estrategia()
        funcao_estrategia, nome_estrategia = importar_estrategia(numero_estrategia)
        
        if funcao_estrategia is None:
            print("❌ Não foi possível carregar a estratégia. Encerrando...")
            return
        
        print(f"\\n✓ Estratégia selecionada: {nome_estrategia}")
        
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
        log_dir = f"logs/estrategia_{numero_estrategia}_{timestamp}"
        os.makedirs(log_dir, exist_ok=True)
        print(f"✓ Pasta de logs criada: {log_dir}")
        
        # 5. Executar Estratégia Escolhida
        print(f"\\n4. Executando {nome_estrategia}...")
        resultado_estrategia = funcao_estrategia(
            SYMBOL, ALOCACAO_POR_ENTRADA, TIMEFRAME, df_candles
        )
        
        # 6. Gerar logs CSV
        print("\\n5. Gerando logs CSV...")
        _save_strategy_logs(resultado_estrategia, log_dir, SYMBOL, TIMEFRAME)
        
        # 7. Imprimir relatório no console
        print("\\n6. Relatório de Resultados:")
        _print_strategy_report(resultado_estrategia, SYMBOL, TIMEFRAME)
        
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
    Imprime o relatório formatado de uma estratégia, incluindo valor inicial, valor final e lucro
    """
    estrategia_nome = resultado_estrategia['estrategia'].upper()
    results = resultado_estrategia['results_by_combo']
    winner = resultado_estrategia['winner']

    # Valor inicial padrão para simulação
    valor_inicial = 100.0

    print(f"\\n=== Estratégia: {estrategia_nome} ({symbol} / {interval}) ===")
    print(f"{'combo':<8} {'retorno%':<10} {'trades':<8} {'win_rate%':<10} {'valor_inicial':<15} {'valor_final':<12} {'lucro':<10}")
    print("-" * 82)

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

        # Calcula valor final e lucro
        valor_final = valor_inicial * (1 + retorno / 100.0)
        lucro = valor_final - valor_inicial

        # Formata o retorno com sinal
        retorno_str = f"{retorno:+.2f}%"
        win_rate_str = f"{win_rate:.2f}" if trades > 0 else "0.00"

        print(f"{combo:<8} {retorno_str:<10} {trades:<8} {win_rate_str:<10} {valor_inicial:<15.2f} {valor_final:<12.2f} {lucro:<10.2f}")

    # Destaca a vencedora
    winner_retorno = f"{winner['retorno_pct']:+.2f}%"
    winner_valor_final = valor_inicial * (1 + winner['retorno_pct'] / 100.0)
    winner_lucro = winner_valor_final - valor_inicial
    print(f"\\nVencedora ({estrategia_nome.title()}): {winner['combo']}  |  {winner_retorno}  |  Valor final: {winner_valor_final:.2f}  |  Lucro: {winner_lucro:.2f}")

if __name__ == "__main__":
    main()

