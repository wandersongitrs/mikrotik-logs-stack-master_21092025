#!/usr/bin/env python3
"""
Módulo para alertas Mikrotik via Telegram
Lê configurações do .env e envia alertas formatados para drops
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Carregar variáveis do .env se existir
def load_env():
    """Carrega variáveis do arquivo .env na mesma pasta"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            logger.warning("python-dotenv não instalado, usando apenas variáveis de ambiente do sistema")

def get_env_vars() -> tuple[Optional[str], Optional[str]]:
    """Obtém as variáveis obrigatórias do ambiente"""
    load_env()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        logger.error("ERRO: TELEGRAM_BOT_TOKEN e/ou TELEGRAM_CHAT_ID não encontrados no .env")
        return None, None
    
    return bot_token, chat_id

def is_drop_event(event: Dict[str, Any]) -> bool:
    """Verifica se o evento indica um Drop"""
    # Verifica action
    action = event.get("action", "")
    if isinstance(action, str) and action.lower() == "drop":
        return True
    
    # Verifica mensagens
    debug_msg = event.get("debug_message", "")
    message = event.get("message", "")
    
    for msg in [debug_msg, message]:
        if isinstance(msg, str) and "drop" in msg.lower():
            return True
    
    return False

def normalize_severity(severity: str) -> str:
    """Normaliza severity removendo duplicações"""
    if not severity:
        return "—"
    
    # Remove duplicações como "info,info"
    parts = [part.strip() for part in severity.split(',')]
    unique_parts = list(dict.fromkeys(parts))  # Remove duplicatas mantendo ordem
    return unique_parts[0].upper() if unique_parts else "—"

def extract_field(event: Dict[str, Any], field_paths: list) -> str:
    """Extrai campo usando múltiplos caminhos possíveis"""
    for path in field_paths:
        # Primeiro tenta como chave literal
        value = event.get(path)
        if value:
            return str(value)
            
        # Se contém ponto, tenta como campo aninhado
        if '.' in path:
            keys = path.split('.')
            temp_value = event
            try:
                for key in keys:
                    temp_value = temp_value[key]
                if temp_value:
                    return str(temp_value)
            except (KeyError, TypeError):
                continue
    
    return "—"

def format_alert_message(event: Dict[str, Any]) -> str:
    """Formata mensagem de alerta para Telegram"""
    # Extrair campos com fallbacks
    timestamp = extract_field(event, ["timestamp", "@timestamp", "time"])
    if timestamp and timestamp != "—":
        try:
            # Tentar formatar timestamp se for ISO
            if 'T' in timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass  # Usar timestamp original se falhar
    
    host_ip = extract_field(event, ["host.ip", "host", "src_host", "device_ip"])
    alert_type = extract_field(event, ["alert_type", "type", "topic"])
    severity = normalize_severity(extract_field(event, ["severity", "level"]))
    priority = extract_field(event, ["priority", "prio"]).upper()
    action = extract_field(event, ["action", "act"])
    protocol = extract_field(event, ["protocol", "proto"])
    
    src_ip = extract_field(event, ["source.ip", "srcip", "src_ip"])
    src_port = extract_field(event, ["source.port", "srcport", "src_port"])
    dst_ip = extract_field(event, ["destination.ip", "dstip", "dst_ip"])
    dst_port = extract_field(event, ["destination.port", "dstport", "dst_port"])
    
    mac = extract_field(event, ["src-mac", "src_mac", "mac", "source_mac"])
    interface = extract_field(event, ["interface", "in_interface", "iface"])
    details = extract_field(event, ["message", "details", "description"])
    
    # Construir mensagem formatada
    message = f"""🚨 MIKROTIK ALERT
📅 {timestamp}
🖥️ Host: {host_ip}
⚠️ Tipo: {alert_type} | Sev: {severity} | Prio: {priority}
❌ Ação: {action} | 🌐 {protocol}
📤 {src_ip}:{src_port} → 📥 {dst_ip}:{dst_port}
🔗 MAC: {mac} | 🔌 Iface: {interface}
💬 {details}"""
    
    return message

def send_telegram_alert(message: str, bot_token: str, chat_id: str) -> bool:
    """Envia alerta para Telegram com retry"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": True
    }
    
    # Retry até 3 tentativas
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("Alerta enviado com sucesso para Telegram")
                return True
            elif 400 <= response.status_code < 500:
                # Erro 4xx - não retry
                logger.error(f"Erro 4xx do Telegram: {response.status_code}")
                return False
            else:
                # Erro 5xx ou timeout - retry
                logger.warning(f"Tentativa {attempt + 1}/3 falhou: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout na tentativa {attempt + 1}/3")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Erro de rede na tentativa {attempt + 1}/3: {e}")
    
    logger.error("Falha ao enviar alerta após 3 tentativas")
    return False

def handle_log(event: Dict[str, Any]) -> bool:
    """
    Função pública principal para processar eventos de log
    
    Args:
        event: Dicionário com dados do evento de log
        
    Returns:
        bool: True se enviou alerta, False se ignorou ou erro
    """
    # Verificar se é evento de Drop
    if not is_drop_event(event):
        logger.debug("Evento ignorado - não é Drop")
        return False
    
    # Obter configurações do .env
    bot_token, chat_id = get_env_vars()
    if not bot_token or not chat_id:
        return False
    
    # Formatar e enviar alerta
    try:
        message = format_alert_message(event)
        success = send_telegram_alert(message, bot_token, chat_id)
        
        if success:
            logger.info("Alerta de Drop processado e enviado")
        else:
            logger.error("Falha ao enviar alerta de Drop")
            
        return success
        
    except Exception as e:
        logger.error(f"Erro ao processar evento: {e}")
        return False

def main():
    """CLI simples para teste"""
    if len(sys.argv) != 2:
        print("Uso: python alerts.py '<json_event>'")
        print("Exemplo: python alerts.py '{\"action\":\"Drop\",\"message\":\"teste\"}'")
        sys.exit(1)
    
    try:
        event_json = sys.argv[1]
        event = json.loads(event_json)
        
        result = handle_log(event)
        print(f"Resultado: {'Enviado' if result else 'Não enviado'}")
        
    except json.JSONDecodeError:
        print("ERRO: JSON inválido")
        sys.exit(1)
    except Exception as e:
        print(f"ERRO: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
