# Status Atual do BotMacroeconomist

Este projeto agora deve ser operado sem depender da API do X.

## Decisoes Operacionais

- `X_COLLECTION_MODE=disabled` e o padrao recomendado.
- `X_ALLOW_MOCK_FALLBACK=False` evita misturar dados de exemplo com producao.
- RSS, sites confiaveis e inputs manuais sao as fontes principais do motor editorial.
- Cada fonte passa a propagar `source_mode` para deixar claro se o dado e `live`, `manual`, `mock` ou `error`.

## Comandos Novos

```bash
python health_check.py
python test_lightweight.py
npm run health
npm run test:light
```

## Dependencias Por Perfil

```bash
python -m pip install -r requirements-core.txt
python -m pip install -r requirements-memory.txt
python -m pip install -r requirements-analytics.txt
python -m pip install -r requirements.txt
```

## Proximo Bloco De Evolucao

1. Refatorar `main.py` em comandos menores.
2. Adicionar testes de pipeline com `pytest` quando o ambiente completo estiver instalado.
3. Criar validacao factual antes de publicar posts/newsletters.
4. Persistir metricas de qualidade por fonte e tema.
