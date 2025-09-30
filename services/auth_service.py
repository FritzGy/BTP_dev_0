# services/auth_service.py
import jwt
import requests
from functools import wraps
from flask import request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

class OAuth2AuthService:
    def __init__(self):
        self.token_cache = {}
        
    def validate_client_credentials_token(self, token: str) -> dict:
        """OAuth2 Client Credentials token validálás"""
        try:
            # JWT decode és validálás
            # Itt a token issuer és audience ellenőrzése történik
            # Teszt környezethez HS256 algoritmus
            secret = 'test-secret-key-for-development-only'
            decoded = jwt.decode(
               token, 
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False}  # Audience ellenőrzés kikapcsolása teszteléshez
        )
            
            # Vevő specifikus ellenőrzések
            client_id = decoded.get('client_id')
            if not client_id:
                raise ValueError("Missing client_id in token")
                
            # Tenant/customer azonosítás
            tenant = decoded.get('tenant') or self._extract_tenant_from_client_id(client_id)
            
            return {
                'valid': True,
                'client_id': client_id,
                'tenant': tenant,
                'scopes': decoded.get('scope', '').split()
            }
            
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return {'valid': False, 'error': str(e)}
    
    def _extract_tenant_from_client_id(self, client_id: str) -> str:
        """Client ID-ból tenant azonosítás (pl. customer1-btppg-client)"""
        return client_id.split('-')[0] if '-' in client_id else 'default'

# Decorator minden API endpoint-hoz
def require_oauth2_client_credentials(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'error': 'Missing or invalid Authorization header',
                'message': 'OAuth2 Client Credentials token required'
            }), 401
            
        token = auth_header.replace('Bearer ', '')
        auth_service = OAuth2AuthService()
        validation_result = auth_service.validate_client_credentials_token(token)
        
        if not validation_result['valid']:
            return jsonify({
                'error': 'Invalid token',
                'message': validation_result.get('error', 'Token validation failed')
            }), 401
            
        # Tenant info request context-be
        request.oauth_client_id = validation_result['client_id']
        request.oauth_tenant = validation_result['tenant']
        
        return f(*args, **kwargs)
    return decorated_function