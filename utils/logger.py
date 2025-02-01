# utils/logger.py
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger():
    logger = logging.getLogger("WebAnalyticsApp")
    logger.setLevel(logging.DEBUG)
    
    if not logger.handlers:
        # Create handlers
        c_handler = logging.StreamHandler()
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        f_handler = RotatingFileHandler(os.path.join(log_dir, 'app.log'), maxBytes=5*1024*1024, backupCount=5)
        c_handler.setLevel(logging.DEBUG)
        f_handler.setLevel(logging.DEBUG)
        
        # Create formatters and add to handlers
        c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        c_handler.setFormatter(c_format)
        f_handler.setFormatter(f_format)
        
        # Add handlers to the logger
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)
    
    return logger
