import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SecurityService:
    """Teljes biztonsági szolgáltatás SQL injection és egyéb támadások ellen"""
    
    def __init__(self):
        self.blocked_attempts = []
        self.security_events = []
        self.setup_patterns()
    
    def setup_patterns(self):
        """Biztonsági minták beállítása - OPTIMALIZÁLT BATCH IMPORTHOZ"""
        # Csak kritikus SQL injection minták (parameterized queries védik az adatokat)
        self.sql_patterns = [
            (r';\s*(DROP|DELETE|TRUNCATE|ALTER)\s+TABLE\b', 'DROP_TABLE'),  # Statement végén
            (r';\s*UNION(\s+ALL)?\s+SELECT\b', 'UNION_SELECT'),  # Statement végén
            (r';\s*--', 'SQL_COMMENT'),  # SQL comment csak statement után
        ]

        # Kritikus mezők, ahol teljes validáció szükséges
        self.critical_fields = {'query', 'sql', 'command', 'script', 'code'}
    
    def is_safe_value(self, key: str, value: str) -> bool:
        """
        Optimalizált biztonsági ellenőrzés BATCH IMPORTHOZ
        - Gyors path: normál data mezőkhöz (name, price, description)
        - Teljes check: kritikus mezőkhöz (query, sql, script)
        """
        if not value:
            return True

        # Hossz ellenőrzés (gyors)
        if len(value) > 5000:
            self._log_security_event('VALUE_TOO_LONG', key, value)
            return False

        # Kritikus mező? Teljes ellenőrzés
        if key.lower() in self.critical_fields:
            return self._full_security_check(key, value)

        # Normál data mező: csak alapvető ellenőrzés
        return self._quick_security_check(key, value)

    def _quick_security_check(self, key: str, value: str) -> bool:
        """Gyors security check normál data mezőkhöz (name, price, category stb.)"""
        value_lower = value.lower()

        # Csak a legveszélyesebb minták
        critical_patterns = ['<script', 'javascript:', '; drop table', '; delete from', '; truncate']
        for pattern in critical_patterns:
            if pattern in value_lower:
                self._log_security_event('CRITICAL_PATTERN', key, value, pattern)
                return False

        return True

    def _full_security_check(self, key: str, value: str) -> bool:
        """Teljes security check kritikus mezőkhöz (query, sql, command)"""
        value_lower = value.lower()

        # SQL injection minták
        for pattern, pattern_name in self.sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                self._log_security_event('SQL_INJECTION_ATTEMPT', key, value, pattern_name)
                return False

        # UPDATE statement check (csak kritikus mezőknél)
        if re.search(r'\bupdate\s+\w+\s+set\b', value_lower):
            self._log_security_event('SQL_UPDATE_DETECTED', key, value)
            return False

        # XSS és script injection
        dangerous = ['<script', 'javascript:', '; drop table', '; delete from', 'exec(', 'eval(']
        for danger in dangerous:
            if danger in value_lower:
                self._log_security_event('DANGEROUS_PATTERN', key, value, danger)
                return False

        return True
    
    def validate_table_name(self, table_name: str) -> bool:
        """Tábla név validálása"""
        if not table_name or len(table_name) > 100:
            return False
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name))
    
    def _log_security_event(self, event_type: str, key: str, value: str, pattern: str = None):
        """Biztonsági esemény naplózása"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'field': key,
            'value': value[:100],  # Truncate for logging
            'pattern': pattern
        }
        
        self.security_events.append(event)
        self.blocked_attempts.append(event)
        
        logger.warning(f"Security event: {event_type} - field: {key}, pattern: {pattern}")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Biztonsági összefoglaló"""
        return {
            'total_events': len(self.security_events),
            'blocked_attempts': len(self.blocked_attempts),
            'recent_events': self.security_events[-10:] if self.security_events else []
        }
    
    def clear_security_log(self):
        """Biztonsági napló törlése"""
        self.security_events.clear()
        self.blocked_attempts.clear()
