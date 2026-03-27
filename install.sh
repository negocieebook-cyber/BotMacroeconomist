#!/bin/bash
# Script de Instalação Rápida para BotMacroeconomist
# Execute: bash install.sh

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🤖 BotMacroeconomist - Script de Instalação            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. Verificar Python
echo "1️⃣  Verificando Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado. Instale Python 3.8+ de https://python.org"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "   ✓ $PYTHON_VERSION encontrado"
echo ""

# 2. Criar virtual environment
echo "2️⃣  Criando virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "   ✓ Virtual environment criado"
else
    echo "   ⚠ Virtual environment já existe"
fi
echo ""

# 3. Ativar virtual environment
echo "3️⃣  Ativando virtual environment..."
source venv/bin/activate
echo "   ✓ Virtual environment ativado"
echo ""

# 4. Atualizar pip
echo "4️⃣  Atualizando pip..."
pip install --upgrade pip setuptools wheel -q
echo "   ✓ pip atualizado"
echo ""

# 5. Instalar dependências
echo "5️⃣  Instalando dependências..."
pip install -r requirements.txt
echo "   ✓ Dependências instaladas"
echo ""

# 6. Criar diretórios necessários
echo "6️⃣  Criando diretórios..."
mkdir -p data/chroma_db
mkdir -p logs
mkdir -p cache
echo "   ✓ Diretórios criados"
echo ""

# 7. Copiar .env.example para .env
echo "7️⃣  Configurando variáveis de ambiente..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "   ✓ Arquivo .env criado (configure com suas chaves)"
else
    echo "   ⚠ Arquivo .env já existe"
fi
echo ""

# 8. Testar instalação
echo "8️⃣  Testando instalação..."
python3 test_setup.py
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║ ✅ INSTALAÇÃO CONCLUÍDA COM SUCESSO!                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🚀 Próximos passos:"
echo ""
echo "1. Configure as duas chaves de API (se desejar):"
echo "   vim .env"
echo ""
echo "2. Execute a demonstração:"
echo "   python3 main.py demo"
echo ""
echo "3. Inicie o agente em produção:"
echo "   python3 main.py"
echo ""
echo "4. Para desativar o scheduler e usar em modo manual:"
echo "   python3 example_usage.py"
echo ""
echo "Para mais informações, leia README.md"
echo ""
