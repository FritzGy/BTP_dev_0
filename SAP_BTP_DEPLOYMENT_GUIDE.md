# SAP BTP Deployment és Konfiguráció Útmutató

## 🎯 Áttekintés

Ez az útmutató bemutatja a btppg-driver alkalmazás telepítését és konfigurálását SAP BTP Kyma környezetben, multi-tenant támogatással és API Key authentikációval.

## 📋 Előfeltételek

- SAP BTP Trial vagy Enterprise account
- Kyma runtime enabled
- Docker registry hozzáférés (Docker Hub, SAP registry, stb.)
- kubectl és kubelogin telepítve

## 🔑 1. API Key Generálás

### Új API Key létrehozása tenant-hez:

```bash
# Python használatával
python3 << 'PYEOF'
import secrets

tenant = "customer1"
environment = "prod"
random_suffix = secrets.token_urlsafe(24)
api_key = f"{tenant}-{environment}-{random_suffix}"

print(f"New API Key for {tenant}/{environment}:")
print(api_key)
print(f"\nEnvironment variable:")
print(f"API_KEY_{tenant.upper()}_{environment.upper()}={api_key}")
PYEOF
```

Példa output:
```
New API Key for customer1/prod:
customer1-prod-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

Environment variable:
API_KEY_CUSTOMER1_PROD=customer1-prod-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

## 🔐 2. Kyma Secret Létrehozása

### Multi-tenant API Key secret:

```bash
# 1. Készítsd el a secret YAML fájlt
cat > api-keys-secret.yaml << 'YAML'
apiVersion: v1
kind: Secret
metadata:
  name: btppg-api-keys
  namespace: default
type: Opaque
stringData:
  # Customer 1 - Production
  API_KEY_CUSTOMER1_PROD: "customer1-prod-abc123def456ghi789jkl012mno345pqr678"

  # Customer 2 - Production
  API_KEY_CUSTOMER2_PROD: "customer2-prod-xyz987uvw654rst321abc098def765ghi432"

  # Demo tenant - Test
  API_KEY_DEMO_TEST: "demo-test-key-for-development-only"

  # Customer 1 - Development
  API_KEY_CUSTOMER1_DEV: "customer1-dev-test123test456test789test012"
YAML

# 2. Apply a secret-et
kubectl apply -f api-keys-secret.yaml

# 3. Ellenőrzés
kubectl get secret btppg-api-keys
```

### Neon PostgreSQL secret:

```bash
cat > neon-db-secret.yaml << 'YAML'
apiVersion: v1
kind: Secret
metadata:
  name: neon-db-secret
  namespace: default
type: Opaque
stringData:
  DATABASE_URL: "postgresql://neondb_owner:password@host.neon.tech/neondb?sslmode=require"
  DB_HOST: "host.neon.tech"
  DB_PORT: "5432"
  DB_NAME: "neondb"
  DB_USER: "neondb_owner"
  DB_PASSWORD: "your-password"
  DB_SSL_MODE: "require"
  DB_PROVIDER: "neon"
  SECRET_KEY: "your-production-secret-key"
YAML

kubectl apply -f neon-db-secret.yaml
```

## 🚀 3. Deployment Frissítése

### Módosítsd a deployment.yaml-t:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: btppg-driver
  namespace: default
spec:
  replicas: 2  # Multi-instance
  selector:
    matchLabels:
      app: btppg-driver
  template:
    metadata:
      labels:
        app: btppg-driver
    spec:
      containers:
      - name: btppg-driver
        image: fritzgy/btppg-driver:v2-apikey  # Új image API key-vel
        ports:
        - containerPort: 8080
        envFrom:
        - secretRef:
            name: neon-db-secret
        - secretRef:
            name: btppg-api-keys  # API keys
        env:
        - name: FLASK_ENV
          value: "production"
        - name: LOG_LEVEL
          value: "INFO"
        - name: MAX_CONTENT_LENGTH
          value: "52428800"  # 50MB
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: btppg-driver
  namespace: default
spec:
  selector:
    app: btppg-driver
  ports:
  - port: 80
    targetPort: 8080
  type: ClusterIP
```

### Deploy:

```bash
kubectl apply -f deployment.yaml
```

## 🌐 4. API Rule / Ingress Létrehozása

### Kyma API Rule (ajánlott):

```yaml
apiVersion: gateway.kyma-project.io/v1beta1
kind: APIRule
metadata:
  name: btppg-driver
  namespace: default
spec:
  gateway: kyma-gateway.kyma-system.svc.cluster.local
  host: btppg-btp.c-96dc39d.kyma.ondemand.com
  service:
    name: btppg-driver
    port: 80
  rules:
    # Public endpoints (health check)
    - path: /health
      methods: ["GET"]
      accessStrategies:
        - handler: noop

    # Protected endpoints (API Key required)
    - path: /api/.*
      methods: ["GET", "POST", "PUT", "DELETE"]
      accessStrategies:
        - handler: noop  # Auth az alkalmazás szintjén (API Key)
```

```bash
kubectl apply -f apirule.yaml

# Várj, míg ready lesz
kubectl get apirule btppg-driver
```

## 📡 5. SAP BTP Destination Konfiguráció

### BTP Cockpit > Connectivity > Destinations:

#### Destination 1: Customer1 Production

```
Name: btppg-driver-customer1-prod
Type: HTTP
URL: https://btppg-btp.c-96dc39d.kyma.ondemand.com

Authentication: NoAuthentication

Additional Properties:
┌────────────────────┬──────────────────────────────────────────────┐
│ Property           │ Value                                        │
├────────────────────┼──────────────────────────────────────────────┤
│ X-API-Key          │ customer1-prod-abc123def456ghi789jkl012      │
│ X-Auth-Email       │ ${user.email}  (vagy fix email)             │
└────────────────────┴──────────────────────────────────────────────┘
```

#### Destination 2: Demo Test

```
Name: btppg-driver-demo
Type: HTTP
URL: https://btppg-btp.c-96dc39d.kyma.ondemand.com

Authentication: BasicAuthentication
User: api-key
Password: demo-test-key-for-development-only

Additional Properties:
┌────────────────────┬──────────────────────────────────────────────┐
│ Property           │ Value                                        │
├────────────────────┼──────────────────────────────────────────────┤
│ X-Auth-Email       │ demo@test.com                                │
└────────────────────┴──────────────────────────────────────────────┘
```

## 🧪 6. Tesztelés

### 1. Health Check (public):

```bash
curl https://btppg-btp.c-96dc39d.kyma.ondemand.com/health
```

Válasz:
```json
{
  "database": "connected",
  "service": "btppg-driver",
  "status": "healthy",
  "version": "1.0.0"
}
```

### 2. CSV Import (API Key header):

```bash
curl -X POST "https://btppg-btp.c-96dc39d.kyma.ondemand.com/api/import/test_products" \
  -H "X-API-Key: demo-test-key-for-development-only" \
  -H "X-Auth-Email: demo@test.com" \
  -F "file=@test_import.csv"
```

### 3. CSV Import (Basic Auth - BTP Destination mód):

```bash
curl -X POST "https://btppg-btp.c-96dc39d.kyma.ondemand.com/api/import/test_products" \
  -u "api-key:demo-test-key-for-development-only" \
  -H "X-Auth-Email: demo@test.com" \
  -F "file=@test_import.csv"
```

### 4. 100K Rekordos Performance Teszt:

```bash
time curl -X POST "https://btppg-btp.c-96dc39d.kyma.ondemand.com/api/import/products_perf" \
  -H "X-API-Key: customer1-prod-abc123def456ghi789jkl012" \
  -H "X-Auth-Email: admin@customer1.com" \
  -F "file=@large_data_100k.csv" \
  --max-time 300
```

Várható eredmény (~10-15 sec):
```json
{
  "status": "success",
  "total_rows": 100000,
  "processed_rows": 100000,
  "skipped_rows": 0,
  "performance": {
    "execution_time_seconds": 12.5,
    "records_per_second": 8000.0,
    "optimization_phase": "phase_3_full_bulk",
    "bulk_insert_count": 100000
  },
  "tenant": "customer1",
  "auth_method": "api_key"
}
```

## 🔄 7. API Key Rotation

### Key rotation folyamat:

```bash
# 1. Generálj új key-t
NEW_KEY=$(python3 -c "import secrets; print('customer1-prod-' + secrets.token_urlsafe(24))")
echo "New key: $NEW_KEY"

# 2. Add hozzá az új key-t a secret-hez (a régi még működik)
kubectl edit secret btppg-api-keys
# Adj hozzá egy új sort: API_KEY_CUSTOMER1_PROD_NEW: "<new-key>"

# 3. Várj a pod restart-ra
kubectl rollout status deployment/btppg-driver

# 4. Frissítsd a BTP Destination-t az új key-vel

# 5. Teszteld az új key-t

# 6. Töröld a régi key-t a secret-ből
kubectl edit secret btppg-api-keys
# Töröld: API_KEY_CUSTOMER1_PROD_OLD

# 7. Restart deployment
kubectl rollout restart deployment/btppg-driver
```

## 📊 8. Monitoring és Logging

### Pod logs:

```bash
# Real-time logs
kubectl logs -f deployment/btppg-driver

# Specific pod
kubectl logs -f btppg-driver-<pod-id>

# Grep API key auth
kubectl logs deployment/btppg-driver | grep "API Key auth"
```

### Metrics endpoint (ha van):

```bash
curl https://btppg-btp.c-96dc39d.kyma.ondemand.com/metrics
```

## 🔒 9. Biztonsági Best Practices

### ✅ DO:
- Használj erős, egyedi API key-ket tenant-enként
- Rotáld a key-eket rendszeresen (pl. 90 naponta)
- Tárol minden key-t Kubernetes Secret-ben
- Használj HTTPS-t mindig
- Audit loggold az API key használatot
- Rate limiting tenant-enként

### ❌ DON'T:
- Ne commitolj API key-eket Git-be
- Ne használj ugyanazt a key-t több tenant-hez
- Ne log-old a teljes API key-t
- Ne tárold a key-eket plain text fájlokban

## 📚 10. Troubleshooting

### Probléma: "Missing API Key"

```bash
# Ellenőrizd a header-t
curl -v -H "X-API-Key: your-key" https://...

# Ellenőrizd a secret-et
kubectl get secret btppg-api-keys -o yaml
```

### Probléma: "Invalid API Key"

```bash
# Ellenőrizd a pod-ban az environment változókat
kubectl exec -it btppg-driver-<pod-id> -- env | grep API_KEY

# Ellenőrizd a logs-ban
kubectl logs btppg-driver-<pod-id> | grep "Invalid API key"
```

### Probléma: Slow import (100K > 30 sec)

```bash
# Ellenőrizd a pod resources-t
kubectl describe pod btppg-driver-<pod-id>

# Növeld a CPU/memory limits-et a deployment-ben
# Restart után újra teszteld
```

## 🎓 11. További Testreszabás

### Tenant-specifikus tábla prefix:

Módosítsd az `import_service.py`-t:
```python
table_name_with_prefix = f"{tenant}_{table_name}"
```

### Rate limiting tenant-enként:

```python
from flask_limiter import Limiter

limiter = Limiter(
    key_func=lambda: request.tenant,  # Tenant alapú limiting
    default_limits=["1000 per hour"]
)

@limiter.limit("100 per minute")
@require_api_key
def import_file(table_name):
    ...
```

## 📞 Support

- Issues: https://github.com/your-repo/issues
- Documentation: https://docs.your-company.com
- SAP Community: https://community.sap.com
