import jwt
import time

payload = {
    'client_id': 'customer-demo-btppg-client',
    'tenant': 'customer-demo',
    'scope': 'btppg:read btppg:write',
    'exp': int(time.time()) + 7200,  # 2 óra
    'iat': int(time.time())
}

secret = 'test-secret-key-for-development-only'
token = jwt.encode(payload, secret, algorithm='HS256')
print(f"Demo OAuth2 Token (2h validity):\n{token}")
