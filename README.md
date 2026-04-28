# BotMacroeconomist - Agente Macroeconomista Autônomo 🤖📊

Um agente IA especializado em macroeconomia que coleta, processa e analisa dados de **5 principais APIs económicas globais**, mantendo memória persistente com embeddings semânticos e executando pesquisas semanais automatizadas.

## 🎯 Funcionalidades Principais

### 📡 APIs Integradas (100% Gratuitas)
- **FRED** (Federal Reserve Economic Data): PIB, Inflação, Juros, Desemprego
- **IMF** (International Monetary Fund): Dados Globais, Outlook Econômico  
- **World Bank**: Indicadores Econômicos de 200+ países
- **OECD**: Índices Antecedentes, Produtividade, Confiança
- **BIS**: Crédito Global, Derivativos, Preços Imobiliários

### 🧠 Sistema de Memória Persistente
- **ChromaDB**: Armazenamento de embeddings com busca semântica
- **Sentence Transformers**: Embeddings locais gratuitos (22MB)
- Busca por query natural: "o que é inflação no Brasil?"

### ⏰ Agendamento Semanal Automático
```
Segunda (14:00 UTC):  Inflação e Política Monetária → FRED + IMF
Terça:                 Crescimento Econômico → World Bank + FRED  
Quarta:                Mercado de Trabalho → FRED + World Bank
Quinta:                Comércio e Finanças → IMF + BIS
Sexta:                 Previsões e Consensus → IMF + OECD + FRED
```

### 📈 Análise Inteligente
- Detecção de anomalias com Z-score
- Correlação entre indicadores
- Previsões simples (linear/exponencial)
- Tendência automática

## ⚡ Quick Start

### 1. Instalação

```bash
# Clonar ou navegar para o diretório
cd BotMacroeconomist

# Criar virtual environment
python -m venv venv

# Ativar virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### Atalho com npm

```bash
# Depois de instalar as dependencias Python, voce tambem pode subir com:
npm run dev
```

Se o PowerShell bloquear o comando `npm` por policy do Windows, use:

```bash
npm.cmd run dev
```

### 2. Configurar API Keys (Opcionalmente)

```bash
# Criar arquivo .env
cp .env.example .env

# Editar .env
export FRED_API_KEY="sua_chave_fred"
# IMF, World Bank, OECD, BIS não requerem chaves (gratuitas!)
```

### 3. Executar

```bash
# Modo completo recomendado: scheduler + memoria + respostas no Telegram
python main.py start

# Atalho equivalente via npm
npm run dev

# Atalho: sem argumentos, sobe o modo completo
python main.py

# Modo Demo (execução manual)
python main.py demo

# Fazer uma pergunta direta sobre o que o bot aprendeu
python main.py ask "o que voce aprendeu hoje sobre inflacao?"

# Carregar a base curada da estrutura seeded
python main.py bootstrap-learning

# Ver catalogo de contas e materiais curados
python main.py learning-catalog

# Entrar em modo de conversa no terminal
python main.py chat

# Escutar mensagens no Telegram e responder usando a memoria
python main.py telegram-listen

# Executar exemplos
python example_usage.py
```

## 📚 Estrutura do Projeto

```
BotMacroeconomist/
├── apis/                      # Clientes das 5 APIs
│   ├── fred_api.py           # Federal Reserve
│   ├── imf_api.py            # International Monetary Fund
│   ├── worldbank_api.py      # World Bank
│   ├── oecd_api.py           # OECD
│   └── bis_api.py            # Bank for International Settlements
│
├── memory/                    # Sistema de memória
│   ├── chromadb_manager.py   # Gerenciador ChromaDB
│   └── embeddings.py         # Gerenciador de embeddings
│
├── agents/                    # Agentes inteligentes
│   └── macroeconomist.py     # Agente principal
│
├── scheduler/                 # Agendamento de tarefas
│   └── weekly_schedule.py    # Scheduler semanal
│
├── analysis/                  # Análise de dados
│   └── macro_analyzer.py     # Analisador macroeconômico
│
├── utils/                     # Utilitários
│   ├── logger.py             # Sistema de logging
│   └── helpers.py            # Funções auxiliares
│
├── config.py                 # Configurações centralizadas
├── requirements.txt          # Dependências Python
├── main.py                   # Ponto de entrada
└── README.md                 # Esta documentação
```

## 🚀 Uso Avançado

### Exemplo 1: Inicializar e Coletar Dados

```python
from agents.macroeconomist import MacroeconomistAgent

# Criação
agent = MacroeconomistAgent(enable_scheduler=False)

# Coletar inflação
inflation = agent.monday_inflation_policy()
print(inflation)

# Coletar crescimento
growth = agent.tuesday_economic_growth()

# Encerrar
agent.shutdown()
```

### Exemplo 2: Buscar na Memória

```python
# Busca semântica
results = agent.search_knowledge(
    "qual foi a taxa de crescimento do PIB em 2023?",
    n_results=5
)

for result in results['results']:
    print(f"API: {result['api']}")
    print(f"Score: {1 - result['distance']:.3f}")
    print(f"Dados: {result['document'][:100]}...")
```

### Exemplo 3: Análise de Indicadores

```python
# Analisar indicador específico
analysis = agent.analyze_indicator("CPI")
print(f"Indicador: {analysis['indicator']}")
print(f"Dados históricos: {len(analysis['historical_data']['results'])} pontos")
```

### Exemplo 4: Status do Agente

```python
status = agent.get_agent_status()
print(f"Documentos na memória: {status['memory']['total_documents']}")
print(f"Taxa de sucesso: {status['task_stats']['success_rate']:.1f}%")
```

## Aprendizado Curado

O projeto agora aceita a estrutura seeded sem substituir o fluxo macro principal.

### O que foi incorporado
- `knowledge/seed_profiles.json`
- `knowledge/cards/*.md`
- `learn/bootstrap_user_context.py`

### Como ativar

```bash
python main.py bootstrap-learning
python main.py learning-catalog
```

Essas sementes passam a ficar disponiveis na mesma memoria usada pelo agente.
## 📊 Dados Coletados

### Inflação (Segunda)
- CPI (Consumer Price Index) - FRED
- PCE (Personal Consumption Expenditures) - FRED
- Inflação Global - IMF WEO
- Taxa FEDFUNDS - FRED

### Crescimento (Terça)
- PIB Nominal (200+ países) - World Bank
- Taxa de Crescimento do PIB - World Bank
- PIB Real US - FRED
- GDPNow Forecast - FRED

### Mercado de Trabalho (Quarta)
- Taxa de Desemprego US - FRED
- Non-Farm Payrolls - FRED
- Desemprego Global - World Bank
- Participação na força de trabalho

### Comércio e Finanças (Quinta)
- Balanço de Pagamentos - IMF
- Investimento Direto Estrangeiro - IMF/World Bank
- Crédito Global - BIS
- Derivativos - BIS

### Previsões (Sexta)
- World Economic Outlook - IMF (2026-2027)
- Índices Antecedentes - OECD
- Confiança do Consumidor - OECD
- Consensus Forecasts - FRED

## 🔑 Configuração de APIs

### FRED (Federal Reserve)
```
📌 Gratuita - Requer chave (obtenha em: fred.stlouisfed.org/docs/api)
⏱️ Limite: ~120 requisições/minuto
📊 Atualização: Diária/Semanal
```

### IMF SDMX
```
📌 Completamente Gratuita
⏱️ Limite: Generoso (1000+ req/dia)
📊 Atualização: Mensal/Trimestral
```

### World Bank
```
📌 Completamente Gratuita  
⏱️ Limite: Generoso
📊 Atualização: Anual/Trimestral
```

### OECD
```
📌 Completamente Gratuita
⏱️ Limite: Generoso
📊 Atualização: Mensal/Trimestral
```

### BIS
```
📌 Completamente Gratuita
⏱️ Limite: Generoso
📊 Atualização: Trimestral/Mensal
```

## 💾 Armazenamento de Dados

### ChromaDB
- **Tamanho**: ~1MB/semana (eficiente!)
- **Retenção**: Ilimitada (configure conforme necessário)
- **Path**: `./data/chroma_db/`
- **Busca**: Semântica com cosine similarity

### Cache
- **Tipo**: Em memória com TTL
- **Expiração**: 6 horas (configurável)
- **Path**: `./cache/`

### Logs
- **Path**: `./logs/macroeconomist.log`
- **Rotação**: 10MB (5 backups)
- **Nível**: INFO (configurável)

## 📞 Troubleshooting

### Erro: "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### Erro: "Connection refused" nas APIs
- Verificar conexão de internet
- Verificar se a API está disponível (visitar a URL manualmente)
- Verificar firewall

### ChromaDB não inicializa
```bash
# Limpar e reinicializar
rm -rf ./data/chroma_db/
python main.py demo
```

### Baixa performance
- Reduzir `MAX_EMBEDDINGS_PER_BATCH` em config.py
- Aumentar `CACHE_EXPIRY_HOURS`
- Usar modelo menor: `all-MiniLM-L6-v2` (padrão)

## 🔐 Segurança

- ✅ Nenhuma chave de API armazenada em código
- ✅ Configurações em `.env` (não commitar)
- ✅ Sem envio de dados para serviços externos (exceto APIs oficiais)
- ✅ ChromaDB local (dados nunca saem do seu servidor)

## 📈 Próximos Passos

- [ ] Integração com LLM para análise narrativa
- [ ] Dashboard web em tempo real
- [ ] Alertas por email/Telegram
- [ ] Backup automático em nuvem
- [ ] Integração com mais APIs (ECB, BoE, BoJ)
- [ ] Análise de correlação avançada
- [ ] Previsões ML (LSTM, Prophet)

## 📄 Licença

MIT License - Use livremente para fins comerciais e pessoais

## 👨‍💼 Suporte

Para dúvidas sobre as APIs:
- FRED: https://fred.stlouisfed.org/docs/api
- IMF: https://www.imf.org/en/Data/API
- World Bank: https://data.worldbank.org/docs/api
- OECD: https://stats.oecd.org/
- BIS: https://www.bis.org/

---

**Desenvolvido com ❤️ para macroeconomistas do futuro** 🚀

