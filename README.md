# Bonde do Ouro - Robô Trader

Este projeto é um exemplo de estrutura para um **robô trader** em Python.

---

## 📦 Estrutura do Projeto

```
bonde-do-ouro-teste/
├── src/
│   ├── main.py
│   ├── strategies/
│   │   └── simple_strategy.py
│   └── utils/
│       └── indicators.py
├── data/
│   └── sample_data.csv
├── tests/
│   └── test_main.py
├── README.md
└── requirements.txt
```

---

## 🚀 Como rodar o projeto

1. Clone o repositório:
   ```sh
   git clone https://github.com/seu-usuario/bonde-do-ouro-teste.git
   ```
2. Instale as dependências:
   ```sh
   pip install -r requirements.txt
   ```
3. Execute o robô:
   ```sh
   python src/main.py
   ```

---

## 🖼️ Exemplo de Imagem

![Exemplo de Gráfico](https://matplotlib.org/stable/_images/sphx_glr_plot_001.png)

---

## 📝 Exemplo de Código

```python
# src/main.py
from strategies.simple_strategy import SimpleStrategy

if __name__ == "__main__":
    strategy = SimpleStrategy()
    strategy.run()
```

---

## ✅ Testes

Para rodar os testes, utilize:
```sh
pytest tests/
```

---

## 📄 Licença

Este projeto está sob a licença MIT.

---

## ✨ Contribuindo

Sinta-se à vontade para abrir issues e