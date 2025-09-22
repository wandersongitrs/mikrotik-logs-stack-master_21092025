from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx
import os
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import hashlib
from collections import defaultdict, deque
from datetime import datetime
from config import *

app = FastAPI(title="Mikrotik Logs Telegram Bridge", version="1.0.0")

# Configuration from config.py
# TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are already imported

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")

# Rate limiting and deduplication
RATE_LIMIT = 20  # messages per minute
DEDUP_WINDOW = 60  # seconds
MIN_SEVERITY = "info"

# In-memory storage for rate limiting and deduplication
message_queue = deque()
message_hashes = defaultdict(float)

class LogMessage(BaseModel):
    timestamp: str = Field(alias="@timestamp")
    host: str
    topic: str
    severity: str
    action: Optional[str] = None
    proto: Optional[str] = None
    srcip: Optional[str] = None
    srcport: Optional[str] = None
    dstip: Optional[str] = None
    dstport: Optional[str] = None
    message: str
    priority: Optional[str] = None
    alert_type: Optional[str] = None
    src_mac: Optional[str] = None
    in_interface: Optional[str] = None
    conn_state: Optional[str] = None

def check_rate_limit() -> bool:
    """Check if we're within rate limit"""
    current_time = time.time()
    
    # Remove old messages from queue
    while message_queue and current_time - message_queue[0] > 60:
        message_queue.popleft()
    
    return len(message_queue) < RATE_LIMIT

def check_deduplication(message_hash: str) -> bool:
    """Check if message is duplicate within dedup window"""
    current_time = time.time()
    
    if message_hash in message_hashes:
        if current_time - message_hashes[message_hash] < DEDUP_WINDOW:
            return False  # Duplicate found
        else:
            del message_hashes[message_hash]  # Remove old entry
    
    message_hashes[message_hash] = current_time
    return True

def create_message_hash(log_data: LogMessage) -> str:
    """Create hash for deduplication"""
    # Create hash based on key fields to identify similar messages
    hash_string = f"{log_data.host}:{log_data.topic}:{log_data.severity}:{log_data.message}"
    return hashlib.md5(hash_string.encode()).hexdigest()

def format_telegram_message(log_data: LogMessage) -> str:
    """Format log message for Telegram"""
    # Parse and format timestamp
    timestamp = log_data.timestamp
    try:
        # Parse ISO timestamp and format to Brazilian time
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        formatted_time = dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception as e:
        print(f"Error parsing timestamp {timestamp}: {e}")
        formatted_time = timestamp[:19] if len(timestamp) > 19 else timestamp
    
    # Clean severity (remove duplicates)
    severity = log_data.severity
    if ',' in severity:
        severity_parts = [s.strip() for s in severity.split(',')]
        severity = severity_parts[0]  # Take first part only
    
    # Determine alert emoji based on priority/type
    if log_data.priority == "high" or log_data.alert_type == "firewall_drop":
        header_emoji = "🔥"
        priority_emoji = "🔴"
    elif log_data.priority == "critical":
        header_emoji = "🚨"
        priority_emoji = "🔴"
    else:
        header_emoji = "⚠️"
        priority_emoji = "🟡"
    
    # Base message with improved formatting
    message_parts = [
        f"{header_emoji} **FIREWALL BLOCKED**",
        f"🕐 {formatted_time}",
        ""
    ]
    
    # Firewall Drop specific format
    if log_data.action == "Drop":
        # Extract rule name from message for better context
        rule_name = "Default Deny"
        if "[" in log_data.message and "]" in log_data.message:
            try:
                rule_part = log_data.message.split("[")[1].split("]")[0]
                if ":" in rule_part:
                    rule_name = rule_part.split(":", 1)[1].strip()
            except:
                pass
        
        # Connection info with better formatting
        if log_data.srcip and log_data.dstip:
            src_info = f"📤 **Origem:** {log_data.srcip}:{log_data.srcport or '0'}"
            dst_info = f"📥 **Destino:** {log_data.dstip}:{log_data.dstport or '0'}"
            
            message_parts.extend([
                f"🚫 **Regra:** {rule_name}",
                f"🌐 **Protocolo:** {log_data.proto or 'UDP'}",
                f"🔌 **Interface:** {log_data.in_interface or 'Unknown'}",
                "",
                src_info,
                dst_info
            ])
            
            # Add MAC if available
            if log_data.src_mac and log_data.src_mac != "unknown":
                message_parts.append(f"🏷️ **MAC:** {log_data.src_mac}")
                
            # Add broadcast/multicast detection
            if log_data.dstip == "255.255.255.255":
                message_parts.append("📢 **Tipo:** Broadcast")
            elif log_data.dstip.startswith("224."):
                message_parts.append("📡 **Tipo:** Multicast")
        
    else:
        # Other alert types
        message_parts.extend([
            f"📋 **{log_data.topic.upper()}**",
            f"⚠️ {severity.title()}"
        ])
        
        if log_data.priority:
            message_parts.append(f"{priority_emoji} {log_data.priority.upper()}")
    
    # Add compact footer
    message_parts.extend([
        "",
        f"🔍 **Log:** {log_data.message[:80]}..." if len(log_data.message) > 80 else f"🔍 **Log:** {log_data.message}"
    ])
    
    return "\n".join(message_parts)

async def send_telegram_message(message: str) -> bool:
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            })
            
            if response.status_code == 200:
                return True
            else:
                print(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error sending to Telegram: {e}")
            return False

@app.post("/notify")
async def notify_telegram(log_data: LogMessage):
    """Receive log data and send to Telegram if conditions are met"""
    
    print(f"DEBUG: Received log - topic: {log_data.topic}, severity: {log_data.severity}, action: {log_data.action}")
    
    # Check severity filter
    severity_levels = ["critical", "error", "warning", "info", "system", "firewall"]
    try:
        current_severity_index = severity_levels.index(log_data.severity.lower())
        min_severity_index = severity_levels.index(MIN_SEVERITY.lower())
        
        if current_severity_index > min_severity_index:
            print(f"DEBUG: Skipping due to severity - {log_data.severity}")
            return JSONResponse(content={"status": "skipped", "reason": "severity too low"})
    except ValueError:
        # If severity not in list, allow it
        print(f"DEBUG: Severity not in list, allowing - {log_data.severity}")
        pass
    
    # Check rate limit
    if not check_rate_limit():
        print("DEBUG: Rate limited")
        return JSONResponse(content={"status": "rate_limited"}, status_code=429)
    
    # Check deduplication
    message_hash = create_message_hash(log_data)
    if not check_deduplication(message_hash):
        print("DEBUG: Duplicate message")
        return JSONResponse(content={"status": "duplicate"})
    
    print("DEBUG: Formatting message for Telegram")
    # Format message
    try:
        telegram_message = format_telegram_message(log_data)
        print(f"DEBUG: Formatted message: {telegram_message[:100]}...")
    except Exception as e:
        print(f"ERROR: Failed to format message: {e}")
        return JSONResponse(content={"status": "format_error", "error": str(e)}, status_code=500)
    
    # Send to Telegram
    print("DEBUG: Sending to Telegram")
    success = await send_telegram_message(telegram_message)
    
    if success:
        # Add to rate limit queue
        message_queue.append(time.time())
        print("DEBUG: Message sent successfully")
        return JSONResponse(content={"status": "sent"})
    else:
        print("DEBUG: Failed to send to Telegram")
        return JSONResponse(content={"status": "failed"}, status_code=500)

@app.post("/drop-forward")
async def forward_drop_logs(request: Request):
    """Endpoint para encaminhar logs brutos que contenham 'Drop' para o Telegram"""
    try:
        # Receber dados como dict
        log_data = await request.json()
        
        # Verificar se é um log com Drop
        log_message = log_data.get("message", "")
        log_action = log_data.get("action", "")
        
        # Verifica se contém "Drop" em qualquer campo
        contains_drop = False
        for value in log_data.values():
            if isinstance(value, str) and "drop" in value.lower():
                contains_drop = True
                break
        
        if not contains_drop:
            return JSONResponse(content={"status": "ignored", "reason": "no drop detected"})
        
        # Formatar mensagem no estilo original do Telegram
        timestamp = log_data.get("timestamp", log_data.get("@timestamp", ""))
        host = log_data.get("host", "")
        topic = log_data.get("topic", log_data.get("alert_type", ""))
        severity = log_data.get("severity", "")
        priority = log_data.get("priority", "")
        action = log_data.get("action", "")
        protocol = log_data.get("protocol", log_data.get("proto", ""))
        src_ip = log_data.get("source.ip", log_data.get("srcip", ""))
        src_port = log_data.get("source.port", log_data.get("srcport", ""))
        dst_ip = log_data.get("destination.ip", log_data.get("dstip", ""))
        dst_port = log_data.get("destination.port", log_data.get("dstport", ""))
        mac = log_data.get("src-mac", log_data.get("src_mac", ""))
        interface = log_data.get("interface", log_data.get("in_interface", ""))
        details = log_data.get("message", "")
        
        # Formatar timestamp
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                formatted_time = dt.strftime("%d/%m/%Y %H:%M:%S")
            else:
                formatted_time = "N/A"
        except Exception as e:
            print(f"Error parsing timestamp in drop-forward {timestamp}: {e}")
            formatted_time = timestamp[:19] if timestamp and len(timestamp) > 19 else timestamp or "N/A"
        
        # Formatar mensagem no novo estilo
        message_parts = [
            "🔥 **MIKROTIK ALERT**",
            f"📅 {formatted_time}",
            "",
            "🛡️ **FIREWALL DROP**"
        ]
        
        if protocol and interface:
            message_parts.append(f"📍 {protocol} • {interface}")
        elif protocol:
            message_parts.append(f"📍 {protocol}")
        
        if src_ip and dst_ip:
            src_info = f"{src_ip}:{src_port}" if src_port else src_ip
            dst_info = f"{dst_ip}:{dst_port}" if dst_port else dst_ip
            message_parts.append(f"🔗 {src_info} → {dst_info}")
        
        if mac:
            message_parts.append(f"🏷️ {mac}")
        
        message_parts.extend([
            "─" * 25,
            f"💬 {details}"
        ])
        
        telegram_message = "\n".join(message_parts)
        
        # Enviar para Telegram
        success = await send_telegram_message(telegram_message)
        
        if success:
            return JSONResponse(content={"status": "sent", "format": "original"})
        else:
            return JSONResponse(content={"status": "failed"}, status_code=500)
            
    except Exception as e:
        print(f"Error in /drop-forward endpoint: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/stats")
async def get_stats():
    """Get current statistics"""
    current_time = time.time()
    
    # Clean up old hashes
    active_hashes = {k: v for k, v in message_hashes.items() 
                     if current_time - v < DEDUP_WINDOW}
    
    return {
        "rate_limit": {
            "current": len(message_queue),
            "limit": RATE_LIMIT,
            "window": "60 seconds"
        },
        "deduplication": {
            "active_hashes": len(active_hashes),
            "window": f"{DEDUP_WINDOW} seconds"
        },
        "timestamp": current_time
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
