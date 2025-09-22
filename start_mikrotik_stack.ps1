# Script para iniciar o Mikrotik Logs Stack isoladamente
# Evita conflitos com outros projetos Docker

Write-Host "🚀 Iniciando Mikrotik Logs Stack..." -ForegroundColor Green
Write-Host "📁 Diretório: $(Get-Location)" -ForegroundColor Cyan

# Verificar se o arquivo .env existe
if (-not (Test-Path "env")) {
    Write-Host "❌ Arquivo 'env' não encontrado!" -ForegroundColor Red
    Write-Host "💡 Certifique-se de que o arquivo env está no diretório atual" -ForegroundColor Yellow
    exit 1
}

# Parar containers existentes do projeto Mikrotik
Write-Host "🛑 Parando containers existentes do Mikrotik..." -ForegroundColor Yellow
docker-compose --env-file env down 2>$null

# Iniciar todos os serviços
Write-Host "▶️ Iniciando todos os serviços..." -ForegroundColor Green
docker-compose --env-file env up -d

# Aguardar inicialização
Write-Host "⏳ Aguardando inicialização dos serviços..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Verificar status dos containers
Write-Host "`n📊 Status dos Containers:" -ForegroundColor Cyan
docker ps --filter "name=mikrotik" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Testar serviços
Write-Host "`n🔍 Testando Serviços:" -ForegroundColor Cyan

# Testar Elasticsearch
try {
    $elasticsearch = Invoke-WebRequest -Uri "http://localhost:9200" -TimeoutSec 5
    Write-Host "✅ Elasticsearch: OK (Porta 9200)" -ForegroundColor Green
} catch {
    Write-Host "❌ Elasticsearch: Erro" -ForegroundColor Red
}

# Testar Kibana
try {
    $kibana = Invoke-WebRequest -Uri "http://localhost:5601" -TimeoutSec 5
    Write-Host "✅ Kibana: OK (Porta 5601)" -ForegroundColor Green
} catch {
    Write-Host "❌ Kibana: Erro" -ForegroundColor Red
}

# Testar Grafana
try {
    $grafana = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 5
    Write-Host "✅ Grafana: OK (Porta 3000)" -ForegroundColor Green
} catch {
    Write-Host "❌ Grafana: Erro" -ForegroundColor Red
}

# Testar Telegram Bridge
try {
    $telegram = Invoke-WebRequest -Uri "http://localhost:8081/health" -TimeoutSec 5
    Write-Host "✅ Telegram Bridge: OK (Porta 8081)" -ForegroundColor Green
} catch {
    Write-Host "❌ Telegram Bridge: Erro" -ForegroundColor Red
}

Write-Host "`n🌐 URLs de Acesso:" -ForegroundColor Cyan
Write-Host "📊 Elasticsearch: http://localhost:9200" -ForegroundColor White
Write-Host "📈 Kibana: http://localhost:5601" -ForegroundColor White
Write-Host "📉 Grafana: http://localhost:3000 (admin/admin)" -ForegroundColor White
Write-Host "🤖 Telegram Bridge: http://localhost:8081" -ForegroundColor White

Write-Host "`n✅ Mikrotik Logs Stack iniciado com sucesso!" -ForegroundColor Green
Write-Host "💡 Use 'docker-compose --env-file env down' para parar todos os serviços" -ForegroundColor Yellow

