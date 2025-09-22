# Script para parar o Mikrotik Logs Stack
# Para apenas os containers deste projeto sem afetar outros

Write-Host "🛑 Parando Mikrotik Logs Stack..." -ForegroundColor Yellow
Write-Host "📁 Diretório: $(Get-Location)" -ForegroundColor Cyan

# Verificar se o arquivo .env existe
if (-not (Test-Path "env")) {
    Write-Host "❌ Arquivo 'env' não encontrado!" -ForegroundColor Red
    Write-Host "💡 Certifique-se de que o arquivo env está no diretório atual" -ForegroundColor Yellow
    exit 1
}

# Parar e remover containers do projeto Mikrotik
Write-Host "🛑 Parando containers do Mikrotik..." -ForegroundColor Yellow
docker-compose --env-file env down

# Remover volumes se solicitado
$removeVolumes = Read-Host "🗑️ Deseja remover os volumes de dados? (s/N)"
if ($removeVolumes -eq "s" -or $removeVolumes -eq "S") {
    Write-Host "🗑️ Removendo volumes..." -ForegroundColor Red
    docker-compose --env-file env down -v
    Write-Host "✅ Volumes removidos!" -ForegroundColor Green
}

# Verificar se ainda há containers rodando
$remainingContainers = docker ps --filter "name=mikrotik" --format "{{.Names}}"
if ($remainingContainers) {
    Write-Host "⚠️ Ainda há containers Mikrotik rodando:" -ForegroundColor Yellow
    docker ps --filter "name=mikrotik" --format "table {{.Names}}\t{{.Status}}"
} else {
    Write-Host "✅ Todos os containers Mikrotik foram parados!" -ForegroundColor Green
}

Write-Host "`n📊 Status dos outros containers Docker:" -ForegroundColor Cyan
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

Write-Host "`n✅ Mikrotik Logs Stack parado com sucesso!" -ForegroundColor Green

