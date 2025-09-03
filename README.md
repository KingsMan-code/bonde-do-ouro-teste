# Sistema de Backtesting - Estratégias de Trading

Sistema completo para backtesting de estratégias de trading na Binance com duas estratégias implementadas: Conservadora e Arriscada.

## Estrutura do Projeto

```
/project
├─ main.py                          # Orquestra o fluxo principal
├─ .env                            # Variáveis de ambiente (não versionado)
├─ requirements.txt                # Dependências do projeto
├─ services/
│    ├─ binance_client.py          # Cliente da Binance
│    ├─ account.py                 # Consulta de saldo
│    └─ marketdata.py              # Dados de mercado
├─ strategies/
│    ├─ conservadora.py            # Estratégia Conservadora
│    └─ arriscada.py               # Estratégia Arriscada
└─ logs/                           # Logs de execução (criado em runtime)
```

## Configuração

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

O arquivo `.env` já está configurado com as credenciais da Binance:

```
KEY_BINANCE=sua_api_key
SECRET_BINANCE=sua_api_secret
```

## Parâmetros de Configuração

No arquivo `main.py`, você pode alterar facilmente os parâmetros:

```python
SYMBOL = "BTCUSDT"              # Par de trading
ALOCACAO_POR_ENTRADA = 1.0      # 100% da banca por entrada
TIMEFRAME = "1h"                # Timeframe das candles
LIMIT_CANDLES = 1000            # Número de candles históricas
```

## Estratégias Implementadas

### Estratégia Conservadora
- **Entrada**: Golden Cross (MA curta cruza para cima da MA longa)
- **Saída**: 
  - Take Profit fixo de +1%
  - Stop por Death Cross (o que acontecer primeiro)

### Estratégia Arriscada
- **Entrada**: Golden Cross (MA curta cruza para cima da MA longa)
- **Saída**:
  - Death Cross (regra principal)
  - Stop Loss de -1% (fail-safe)

### Combinações de Médias Móveis Testadas
- (7,21), (8,21), (9,27), (10,30)
- (12,26), (20,50), (21,55), (24,72)

## Execução

```bash
python main.py
```

## Saídas do Sistema

### 1. Console
- Relatório formatado com resultados por estratégia
- Combinações ordenadas por performance
- Destaque da combinação vencedora

### 2. Logs CSV
Pasta `logs/MM-DD-YYYY-HH-mm/` com arquivos:
- `conservadora_BTCUSDT_1h.csv`
- `arriscada_BTCUSDT_1h.csv`

### Colunas dos Logs
- `open_time`, `close_time`: Timestamps das candles
- `open`, `high`, `low`, `close`, `volume`: Dados OHLCV
- `ma_short`, `ma_long`: Valores das médias móveis
- `signal_buy_price`: Preço de entrada (quando aplicável)
- `signal_sell_price`: Preço de saída (quando aplicável)
- `trade_pnl_pct`: P&L da operação em %
- `combo`: Combinação de MAs utilizada
- `estrategia`: Nome da estratégia
- `reason`: Motivo da entrada/saída

## Segurança

- ✅ Todas as operações são simuladas (sem ordens reais)
- ✅ Apenas operações de leitura na API
- ✅ SECRET_BINANCE nunca é logado
- ✅ Suporte apenas ao lado comprado (long only)

## Exemplo de Saída

```
=== Estratégia: CONSERVADORA (BTCUSDT / 1h) ===
combo   retorno%   trades   win_rate%
8x21     +6.42%       7       57.14
7x21     +3.25%       5       60.00
12x26    -1.10%       4       50.00

Vencedora (Conservadora): 8x21  |  +6.42%

=== Estratégia: ARRISCADA (BTCUSDT / 1h) ===
combo   retorno%   trades   win_rate%
10x30    +5.88%      6        50.00
7x21     +5.10%      7        57.14
21x55    -0.75%      3        33.33

Vencedora (Arriscada): 10x30  |  +5.88%
```

