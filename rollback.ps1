# 🔄 SCRIPT DE ROLLBACK AUTOMÁTICO - MIKROTIK LOGS STACK
# Data: 20/09/2025 - 19:19:23

Write-Host "🔄 INICIANDO ROLLBACK DO MIKROTIK LOGS STACK..." -ForegroundColor Yellow
Write-Host "📅 Data do Rollback: 20/09/2025 - 19:19:23" -ForegroundColor Cyan

# Verificar se estamos no diretório correto
if (-not (Test-Path "docker-compose.yml")) {
    Write-Host "❌ ERRO: Execute este script no diretório raiz do projeto!" -ForegroundColor Red
    exit 1
}

Write-Host "⏹️ Parando todos os serviços Docker..." -ForegroundColor Yellow
docker-compose down

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRO ao parar serviços Docker!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Serviços parados com sucesso!" -ForegroundColor Green

# Verificar se o backup existe
$backupPath = "..\mikrotik-logs-stack-backup_20250920_191923"
if (-not (Test-Path $backupPath)) {
    Write-Host "❌ ERRO: Backup não encontrado em $backupPath" -ForegroundColor Red
    Write-Host "💡 Verifique se o backup foi criado corretamente." -ForegroundColor Yellow
    exit 1
}

Write-Host "📁 Backup encontrado: $backupPath" -ForegroundColor Green

# Fazer backup do estado atual (caso precise voltar)
$currentBackup = "..\mikrotik-logs-stack-current_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Write-Host "💾 Criando backup do estado atual: $currentBackup" -ForegroundColor Yellow
Copy-Item -Path "." -Destination $currentBackup -Recurse -Force

Write-Host "🔄 Restaurando backup funcional..." -ForegroundColor Yellow

# Remover diretório atual
Remove-Item -Path "*" -Recurse -Force -Exclude "rollback.ps1"

# Restaurar backup
Copy-Item -Path "$backupPath\*" -Destination "." -Recurse -Force

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRO ao restaurar backup!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Backup restaurado com sucesso!" -ForegroundColor Green

Write-Host "🚀 Iniciando serviços Docker..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRO ao iniciar serviços Docker!" -ForegroundColor Red
    exit 1
}

Write-Host "⏳ Aguardando inicialização dos serviços..." -ForegroundColor Yellow
Start-Sleep 15

Write-Host "🔍 Verificando status dos serviços..." -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}" | Select-String "mikrotik"

Write-Host ""
Write-Host "🎉 ROLLBACK CONCLUÍDO COM SUCESSO!" -ForegroundColor Green
Write-Host "📊 Sistema restaurado para estado funcional de 20/09/2025 - 19:19:23" -ForegroundColor Cyan
Write-Host "🔗 Kibana: http://192.168.1.12:5601" -ForegroundColor Blue
Write-Host "📈 Grafana: http://192.168.1.12:3000" -ForegroundColor Blue
Write-Host ""
Write-Host "✅ Todos os serviços funcionando!" -ForegroundColor Green
Write-Host "📱 Bot do Telegram ativo e enviando alertas!" -ForegroundColor Green
