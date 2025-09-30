# services/apikey_service.py
"""
API Key Authentication Service - SAP BTP Destination kompatibilis
Multi-tenant támogatással

SAP BTP Destination konfiguráció példa:
-------------------------------------------
Type: HTTP
URL: https://btppg-btp.c-96dc39d.kyma.ondemand.com
Authentication: NoAuthentication  # Vagy BasicAuthentication
Additional Properties:
  X-API-Key: <tenant-specific-key>
  X-Auth-Email: <user-email>

Vagy BasicAuthentication használatával:
  User: api-key
  Password: <tenant-specific-key>
"""

import os
import logging
import hashlib
import secrets
from typing import Dict, Optional, List
from functools import wraps
from flask import request, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)


class APIKeyService:
    """
    Multi-tenant API Key kezelés SAP BTP kompatibilitással

    Támogatott módok:
    1. X-API-Key header (ajánlott)
    2. Basic Authentication (SAP BTP Destination default)
    3. Bearer token (backward compatibility)
    """

    def __init__(self):
        self.api_keys = self._load_api_keys()
        self.key_usage_stats = {}

    def _load_api_keys(self) -> Dict[str, Dict]:
        """
        API kulcsok betöltése környezeti változókból vagy Secret-ből

        Formátum:
        API_KEY_<TENANT>_<ENV>=<key_value>

        Példa .env:
        API_KEY_CUSTOMER1_PROD=cust1-prod-abc123def456ghi789
        API_KEY_CUSTOMER2_PROD=cust2-prod-xyz987uvw654rst321
        API_KEY_DEMO_TEST=demo-test-key-for-development
        """
        keys = {}

        # Environment alapú konfiguráció
        for env_var, value in os.environ.items():
            if env_var.startswith('API_KEY_'):
                # Parse: API_KEY_CUSTOMER1_PROD -> customer1, prod
                parts = env_var.replace('API_KEY_', '').lower().split('_')
                if len(parts) >= 2:
                    tenant = parts[0]
                    environment = '_'.join(parts[1:])

                    # Key hash tárolása (security)
                    key_hash = self._hash_key(value)

                    keys[key_hash] = {
                        'tenant': tenant,
                        'environment': environment,
                        'key_preview': value[:8] + '...' + value[-4:],
                        'created_at': datetime.now().isoformat(),
                        'active': True
                    }

                    logger.info(f"Loaded API key for tenant: {tenant}, env: {environment}")

        # Fallback: demo key teszt környezethez
        if not keys:
            logger.warning("No API keys configured, using demo key")
            demo_key = "demo-test-key-for-development-only"
            demo_hash = self._hash_key(demo_key)
            keys[demo_hash] = {
                'tenant': 'demo',
                'environment': 'test',
                'key_preview': 'demo-...only',
                'created_at': datetime.now().isoformat(),
                'active': True
            }

        logger.info(f"Total API keys loaded: {len(keys)}")
        return keys

    def _hash_key(self, api_key: str) -> str:
        """API key hashelés (biztonságos tárolás)"""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """
        API Key validálás - ultra gyors

        Returns:
            Dict with tenant info if valid, None if invalid
        """
        if not api_key:
            return None

        key_hash = self._hash_key(api_key)
        key_info = self.api_keys.get(key_hash)

        if key_info and key_info.get('active'):
            # Usage tracking
            self._track_usage(key_hash)
            return {
                'valid': True,
                'tenant': key_info['tenant'],
                'environment': key_info['environment'],
                'key_hash': key_hash
            }

        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        return None

    def extract_api_key_from_request(self) -> Optional[str]:
        """
        API Key kinyerése request-ből, többféle módon

        Priority:
        1. X-API-Key header (leggyorsabb)
        2. Basic Auth password (SAP BTP Destination default)
        3. Bearer token (backward compatibility)
        """
        # 1. X-API-Key header (ajánlott)
        api_key = request.headers.get('X-API-Key')
        if api_key:
            logger.debug("API Key found in X-API-Key header")
            return api_key

        # 2. Basic Authentication (SAP BTP Destination)
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Basic '):
            try:
                import base64
                # Basic base64(username:password) -> password az API key
                credentials = base64.b64decode(auth_header.replace('Basic ', '')).decode('utf-8')
                username, password = credentials.split(':', 1)
                logger.debug(f"API Key found in Basic Auth (user: {username})")
                return password
            except Exception as e:
                logger.error(f"Basic Auth parsing error: {e}")

        # 3. Bearer token (backward compatibility)
        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            # Rövid token = API key, hosszú JWT = OAuth2
            if len(token) < 200:  # API key-k rövidek
                logger.debug("API Key found in Bearer token")
                return token

        return None

    def _track_usage(self, key_hash: str):
        """API key használat tracking (rate limiting alapja)"""
        if key_hash not in self.key_usage_stats:
            self.key_usage_stats[key_hash] = {
                'total_requests': 0,
                'first_used': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat()
            }

        self.key_usage_stats[key_hash]['total_requests'] += 1
        self.key_usage_stats[key_hash]['last_used'] = datetime.now().isoformat()

    def generate_new_api_key(self, tenant: str, environment: str = 'prod') -> str:
        """
        Új API key generálás

        Formátum: {tenant}-{env}-{random_32_chars}
        Példa: customer1-prod-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
        """
        random_suffix = secrets.token_urlsafe(24)  # 32 char base64
        api_key = f"{tenant}-{environment}-{random_suffix}"

        # Mentés
        key_hash = self._hash_key(api_key)
        self.api_keys[key_hash] = {
            'tenant': tenant,
            'environment': environment,
            'key_preview': api_key[:12] + '...' + api_key[-4:],
            'created_at': datetime.now().isoformat(),
            'active': True
        }

        logger.info(f"Generated new API key for {tenant}/{environment}")
        return api_key

    def revoke_api_key(self, key_hash: str) -> bool:
        """API key visszavonás"""
        if key_hash in self.api_keys:
            self.api_keys[key_hash]['active'] = False
            logger.info(f"Revoked API key: {key_hash[:16]}...")
            return True
        return False

    def list_api_keys(self, tenant: Optional[str] = None) -> List[Dict]:
        """API key-k listázása (admin endpoint)"""
        keys = []
        for key_hash, info in self.api_keys.items():
            if tenant and info['tenant'] != tenant:
                continue

            keys.append({
                'key_hash': key_hash[:16] + '...',
                'tenant': info['tenant'],
                'environment': info['environment'],
                'key_preview': info['key_preview'],
                'created_at': info['created_at'],
                'active': info['active'],
                'usage': self.key_usage_stats.get(key_hash, {})
            })

        return keys

    def get_usage_stats(self) -> Dict:
        """API key használati statisztikák"""
        return {
            'total_keys': len(self.api_keys),
            'active_keys': sum(1 for k in self.api_keys.values() if k['active']),
            'total_requests': sum(s['total_requests'] for s in self.key_usage_stats.values()),
            'keys_usage': self.key_usage_stats
        }


# Global instance
_api_key_service = None

def get_api_key_service() -> APIKeyService:
    """Singleton API Key Service"""
    global _api_key_service
    if _api_key_service is None:
        _api_key_service = APIKeyService()
    return _api_key_service


# Decorator: API Key authentikáció (ajánlott batch importhoz)
def require_api_key(f):
    """
    API Key authentikáció decorator

    Használat:
        @app.route('/api/import/<table>')
        @require_api_key
        def import_data(table):
            tenant = request.tenant  # Automatikusan beállítva
            return jsonify({'status': 'ok'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        service = get_api_key_service()

        # Extract API key
        api_key = service.extract_api_key_from_request()

        if not api_key:
            return jsonify({
                'error': 'Missing API Key',
                'message': 'Provide API key via X-API-Key header, Basic Auth, or Bearer token',
                'documentation': 'https://docs.example.com/api-authentication'
            }), 401

        # Validate API key
        validation = service.validate_api_key(api_key)

        if not validation or not validation.get('valid'):
            return jsonify({
                'error': 'Invalid API Key',
                'message': 'The provided API key is invalid or has been revoked'
            }), 401

        # Set tenant info in request context
        request.tenant = validation['tenant']
        request.environment = validation['environment']
        request.api_key_hash = validation['key_hash']

        logger.info(f"API Key auth successful - Tenant: {request.tenant}, Env: {request.environment}")

        return f(*args, **kwargs)

    return decorated_function


# Decorator: Flexible auth (API Key VAGY OAuth2)
def require_flexible_auth(f):
    """
    Hibrid authentikáció: API Key VAGY OAuth2

    Batch import esetén ajánlott az API Key (gyorsabb),
    de OAuth2 is elfogadott backward compatibility miatt
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Próbáld API Key-t először (gyorsabb)
        service = get_api_key_service()
        api_key = service.extract_api_key_from_request()

        if api_key:
            validation = service.validate_api_key(api_key)
            if validation and validation.get('valid'):
                request.tenant = validation['tenant']
                request.environment = validation['environment']
                request.auth_method = 'api_key'
                return f(*args, **kwargs)

        # Fallback OAuth2-re
        from services.auth_service import OAuth2AuthService
        auth_header = request.headers.get('Authorization', '')

        if auth_header.startswith('Bearer '):
            token = auth_header.replace('Bearer ', '')
            oauth_service = OAuth2AuthService()
            oauth_result = oauth_service.validate_client_credentials_token(token)

            if oauth_result.get('valid'):
                request.tenant = oauth_result['tenant']
                request.oauth_client_id = oauth_result['client_id']
                request.auth_method = 'oauth2'
                return f(*args, **kwargs)

        # Egyik sem érvényes
        return jsonify({
            'error': 'Authentication required',
            'message': 'Provide API Key (X-API-Key) or OAuth2 token (Authorization: Bearer)',
            'documentation': 'https://docs.example.com/api-authentication'
        }), 401

    return decorated_function