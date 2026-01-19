#!/usr/bin/env python3
"""
Example demonstrating automatic config file detection.
"""

from mogger import Mogger

# Example 1: Automatic config file detection
# Mogger will search for mogger_config.yaml in the current directory
try:
    logger = Mogger()  # No config_path needed!
    print("✅ Logger initialized with auto-detected config")
    print(f"Available tables: {logger.get_tables()}")
    
    # Log some messages
    logger.info("Application started", table="system_events", 
                event_type="startup", description="App initialized successfully")
    
    logger.info("User action", table="user_actions",
                user_id="user_123", action="login", ip_address="192.168.1.1")
    
    print("✅ Logs created successfully")
    logger.close()
    
except FileNotFoundError as e:
    print(f"❌ No config file found: {e}")

# Example 2: Explicit config path (still works)
try:
    logger2 = Mogger("mogger_config.yaml")
    print("✅ Logger initialized with explicit config path")
    logger2.close()
except Exception as e:
    print(f"Error: {e}")
