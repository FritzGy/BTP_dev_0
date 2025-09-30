import os
import json
import logging
from typing import Dict, Any

class Config:
    """Konfigurációkezelő osztály SAP BTP környezethez"""
    
    def __init__(self):
        self.db_config = self._load_db_config()
        self.app_config = self._load_app_config()
    
    def _load_db_config(self) -> Dict[str, Any]:
        """PostgreSQL adatbázis konfiguráció betöltése"""
        # SAP BTP Cloud Foundry VCAP_SERVICES környezeti változó kezelése
        vcap_services = os.getenv('VCAP_SERVICES')
        if vcap_services:
            services = json.loads(vcap_services)
            for service_name, service_list in services.items():
                if 'postgresql' in service_name.lower():
                    if service_list:
                        credentials = service_list[0].get('credentials', {})
                        logging.info("Adatbázis konfiguráció betöltve SAP BTP VCAP_SERVICES-ből")
                        return {
                            'host': credentials.get('hostname'),
                            'port': int(credentials.get('port', 5432)),
                            'database': credentials.get('dbname'),
                            'username': credentials.get('username'),
                            'password': credentials.get('password'),
                            'uri': credentials.get('uri'),
                            'provider': 'sap_btp'
                        }
        
        # Fallback: környezeti változókból
        logging.info("Adatbázis konfiguráció betöltve környezeti változókból")
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_NAME', 'btppg_db'),
            'username': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'uri': os.getenv('DATABASE_URL'),
            'provider': 'local'
        }
    
    def _load_app_config(self) -> Dict[str, Any]:
        """Alkalmazás konfiguráció betöltése"""
        return {
            'secret_key': os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'),
            'debug': os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
            'port': int(os.getenv('PORT', '5000')),
            'host': os.getenv('HOST', '0.0.0.0'),
            'max_content_length': int(os.getenv('MAX_CONTENT_LENGTH', '16777216')),
            'upload_folder': os.getenv('UPLOAD_FOLDER', '/tmp'),
            'log_level': os.getenv('LOG_LEVEL', 'INFO')
        }
    
    def get_database_url(self) -> str:
        """PostgreSQL kapcsolati string generálása"""
        if self.db_config.get('uri'):
            return self.db_config['uri']
        
        return (f"postgresql://{self.db_config['username']}:"
                f"{self.db_config['password']}@{self.db_config['host']}:"
                f"{self.db_config['port']}/{self.db_config['database']}")
