# Sistema de Monitoramento de Logs Mikrotik com ELK Stack + Grafana + Telegram

Este projeto implementa um sistema completo de monitoramento de logs para roteadores Mikrotik RB750GR3, utilizando ELK Stack (Elasticsearch, Logstash, Kibana), Grafana e integração com Telegram para notificações em tempo real.

## 🏗️ Arquitetura

```
Mikrotik RB750GR3 → UDP/514 → Logstash → Elasticsearch + Telegram Bridge → Telegram Bot
                                    ↓
                              Grafana (Dashboards)
```

## 📋 Pré-requisitos

- Docker Desktop para Windows 11 Pro
- Porta UDP 514 disponível
- Conexão com internet para download das imagens Docker
- Bot do Telegram configurado (token e chat_id já configurados)

## 🚀 Instalação

### 1. Clone o repositório
```bash
git clone <seu-repositorio>
cd mikrotik-logs-stack
```

### 2. Verifique as variáveis de ambiente
O arquivo `env` já está configurado com:
- `TELEGRAM_BOT_TOKEN`: 6795669873:AAHg8oJzPdByUpLoVAihrzHy-I2v69TApXg
- `TELEGRAM_CHAT_ID`: -4827243101

### 3. Inicie os serviços
```bash
docker compose up -d
```

### 4. Aguarde a inicialização
Os serviços podem levar alguns minutos para inicializar completamente:
- Elasticsearch: ~2-3 minutos
- Kibana: ~1-2 minutos
- Logstash: ~1 minuto
- Grafana: ~30 segundos
- Telegram Bridge: ~30 segundos

## 🌐 Acesso aos Serviços

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Kibana** | http://localhost:5601 | N/A (sem autenticação) |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Elasticsearch** | http://localhost:9200 | N/A (sem autenticação) |
| **Telegram Bridge** | http://localhost:8080 | N/A (API REST) |

## ⚙️ Configuração do Mikrotik

### 1. Acesse o WinBox
Conecte-se ao seu roteador Mikrotik RB750GR3 via WinBox.

### 2. Configure o Syslog
```
System → Logging → Actions
```

**Adicione uma nova ação:**
- **Name**: remote-logs
- **Remote**: 192.168.1.12
- **Remote Port**: 514
- **Remote Log Protocol**: udp
- **Topics**: firewall, info, system, warning, error, critical

### 3. Habilite o Syslog Daemon
```
System → Logging → Settings
```
- **Syslog Daemon**: ✅ Enabled

### 4. Configure as Regras de Logging
```
System → Logging → Rules
```

**Adicione regras para cada tópico:**
- **Topics**: firewall
- **Action**: remote-logs

- **Topics**: info
- **Action**: remote-logs

- **Topics**: system
- **Action**: remote-logs

- **Topics**: warning
- **Action**: remote-logs

- **Topics**: error
- **Action**: remote-logs

- **Topics**: critical
- **Action**: remote-logs

## 📊 Dashboards Disponíveis

### Grafana
O dashboard inclui:
- **Logs por Minuto**: Gráfico temporal de volume de logs
- **Logs por Severidade**: Distribuição por nível de criticidade
- **Logs por Tópico**: Distribuição por categoria
- **Ações de Firewall**: Tipos de ações (accept, drop, etc.)
- **Top 10 IPs de Origem**: IPs que mais geram logs
- **Top 10 IPs de Destino**: IPs mais acessados
- **Logs por Severidade ao Longo do Tempo**: Evolução temporal

### Kibana
- Visualização e busca avançada nos logs
- Análise detalhada dos campos parseados
- Criação de visualizações customizadas

## 🔔 Notificações Telegram

### Funcionalidades
- **Rate Limiting**: Máximo de 20 mensagens por minuto
- **Deduplicação**: Mensagens iguais são filtradas por 60 segundos
- **Filtro de Severidade**: Mínimo = info
- **Formatação Rica**: Mensagens com emojis e formatação Markdown

### Campos Incluídos
- Timestamp
- Host (IP do Mikrotik)
- Tópico
- Severidade
- Ação (para logs de firewall)
- Protocolo
- IP de origem e destino
- Portas de origem e destino
- Mensagem completa

## 🛠️ Comandos Úteis

### Verificar status dos serviços
```bash
docker compose ps
```

### Ver logs de um serviço específico
```bash
docker compose logs elasticsearch
docker compose logs logstash
docker compose logs grafana
docker compose logs telegram_bridge
```

### Reiniciar um serviço
```bash
docker compose restart logstash
```

### Parar todos os serviços
```bash
docker compose down
```

### Parar e remover volumes
```bash
docker compose down -v
```

## 🔍 Troubleshooting

### Logstash não recebe logs
1. Verifique se a porta UDP 514 está aberta
2. Confirme a configuração do Mikrotik
3. Teste com netcat: `echo "test" | nc -u localhost 514`

### Elasticsearch não inicia
1. Verifique se há memória suficiente (mínimo 2GB)
2. Ajuste `ES_JAVA_OPTS` no docker-compose.yml se necessário

### Telegram não recebe mensagens
1. Verifique o token e chat_id no arquivo `env`
2. Confirme se o bot está ativo
3. Teste a API: `curl http://localhost:8080/health`

### Grafana não carrega dashboards
1. Aguarde o Elasticsearch estar completamente inicializado
2. Verifique se o datasource está configurado corretamente
3. Confirme se há dados nos índices

## 📈 Monitoramento

### Endpoints de Saúde
- **Telegram Bridge**: http://localhost:8080/health
- **Estatísticas**: http://localhost:8080/stats
- **Elasticsearch**: http://localhost:9200/_cluster/health

### Logs do Sistema
```bash
# Logs do Logstash
docker compose logs -f logstash

# Logs do Elasticsearch
docker compose logs -f elasticsearch

# Logs do Grafana
docker compose logs -f grafana
```

## 🔧 Personalização

### Adicionar Novos Tópicos
1. Edite `logstash/pipeline/logstash.conf`
2. Adicione o tópico na condição de filtro
3. Configure o Mikrotik para enviar o novo tópico

### Modificar Dashboards
1. Acesse Grafana em http://localhost:3000
2. Edite o dashboard "Mikrotik Logs Dashboard"
3. Salve as alterações

### Ajustar Rate Limiting
Edite `telegram_bridge/app.py`:
- `RATE_LIMIT`: Mensagens por minuto
- `DEDUP_WINDOW`: Janela de deduplicação em segundos
- `MIN_SEVERITY`: Severidade mínima para envio

## 📚 Recursos Adicionais

- [Documentação Elasticsearch](https://www.elastic.co/guide/index.html)
- [Documentação Logstash](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Documentação Grafana](https://grafana.com/docs/)
- [API Telegram Bot](https://core.telegram.org/bots/api)

## 🤝 Suporte

Para problemas ou dúvidas:
1. Verifique os logs dos serviços
2. Consulte a documentação oficial
3. Teste cada componente individualmente
4. Verifique a conectividade de rede

---

**Sistema desenvolvido para monitoramento de logs Mikrotik com integração completa ELK + Grafana + Telegram**
