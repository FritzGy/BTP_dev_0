import uuid
from datetime import datetime, timezone
from typing import Dict, Any

class BaseModel:
    """Alapértelmezett model osztály minden adatbázis táblához"""
    
    @staticmethod
    def generate_uuid() -> str:
        """UUID generálása"""
        return str(uuid.uuid4())
    
    @staticmethod
    def get_current_timestamp() -> datetime:
        """Aktuális időbélyeg lekérése (timezone-aware UTC)"""
        return datetime.now(timezone.utc)
    
    @classmethod
    def add_default_fields(cls, data: Dict[str, Any], auth_email: str) -> Dict[str, Any]:
        """Alapértelmezett mezők hozzáadása egy rekordhoz"""
        current_time = cls.get_current_timestamp()
        
        # Ha nincs UUID, generálunk egyet
        if 'id' not in data or not data['id']:
            data['id'] = cls.generate_uuid()
        
        # Időbélyegek hozzáadása
        if 'created_at' not in data:
            data['created_at'] = current_time
        
        data['updated_at'] = current_time
        data['auth_email'] = auth_email
        
        return data
    
    @classmethod
    def get_table_schema(cls, table_name: str) -> Dict[str, str]:
        """Alapértelmezett tábla séma visszaadása"""
        return {
            'id': 'UUID PRIMARY KEY DEFAULT gen_random_uuid()',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'auth_email': 'VARCHAR(255) NOT NULL'
        }
