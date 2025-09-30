# 🚀 Gyors Deployment - Javított Verzió

## Változtatások ebben a verzióban:

### ✅ Security Service Javítások
- False positive regex-ek kijavítva
- 2-szintű validáció: gyors path normál mezőkhöz, teljes check kritikus mezőkhöz
- ~10x gyorsabb feldolgozás

### ✅ API Key Authentikáció
- Multi-tenant API Key támogatás
- SAP BTP Destination kompatibilis
- 3 auth mód: X-API-Key, Basic Auth, Bearer token
- Flexible auth: API Key VAGY OAuth2

### ✅ Import Teljesítmény
- Várható: 100K rekord ~10-15 sec (korábban timeout/skip)

## 🔧 1. Lokális Teszt (opcionális)

```bash
# Docker build
docker build -t btppg-driver:v2-apikey .

# Lokális run
docker run -p 8080:8080 --env-file .env btppg-driver:v2-apikey

# Teszt (másik terminálban)
curl -X POST http://localhost:8080/api/import/test_local \
  -H "X-API-Key: demo-test-key-for-development-only" \
  -H "X-Auth-Email: test@local.com" \
  -F "file=@test_import.csv"
```

## 🐳 2. Docker Build és Push

```bash
# Login Docker Hub
docker login

# Build új verzió
docker build -t fritzgy/btppg-driver:v2-apikey .

# Tag latest is
docker tag fritzgy/btppg-driver:v2-apikey fritzgy/btppg-driver:latest

# Push
docker push fritzgy/btppg-driver:v2-apikey
docker push fritzgy/btppg-driver:latest
```

## ☁️ 3. Kyma Deployment Frissítés

### A) API Keys Secret létrehozása (ha még nincs):

```bash
cat > api-keys-secret.yaml << 'YAML'
apiVersion: v1
kind: Secret
metadata:
  name: btppg-api-keys
  namespace: default
type: Opaque
stringData:
  API_KEY_DEMO_TEST: "demo-test-key-for-development-only"
  API_KEY_CUSTOMER1_PROD: "customer1-prod-abc123def456ghi789jkl012"
YAML

kubectl apply -f api-keys-secret.yaml
```

### B) Deployment frissítése:

```yaml
# deployment-v2.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: btppg-driver
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: btppg-driver
  template:
    metadata:
      labels:
        app: btppg-driver
        version: v2-apikey
    spec:
      containers:
      - name: btppg-driver
        image: fritzgy/btppg-driver:v2-apikey  # ÚJ IMAGE!
        ports:
        - containerPort: 8080
        envFrom:
        - secretRef:
            name: neon-db-secret
        - secretRef:
            name: btppg-api-keys  # ÚJ SECRET!
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

```bash
# Apply
kubectl apply -f deployment-v2.yaml

# Várj a rollout-ra
kubectl rollout status deployment/btppg-driver

# Ellenőrzés
kubectl get pods -l app=btppg-driver
kubectl logs -l app=btppg-driver --tail=20
```

## 🧪 4. Gyors Teszt

```bash
# Health check
curl https://btppg-btp.c-96dc39d.kyma.ondemand.com/health

# CSV import (2 rekord - most működnie kell!)
curl -X POST "https://btppg-btp.c-96dc39d.kyma.ondemand.com/api/import/test_v2" \
  -H "X-API-Key: demo-test-key-for-development-only" \
  -H "X-Auth-Email: demo@test.com" \
  -F "file=@test_import.csv"

# Várható eredmény:
# "processed_rows": 2  ✅ (nem 0!)
# "status": "success"  ✅
```

## 📊 5. Performance Teszt

```bash
# 10K rekord
time curl -X POST "https://btppg-btp.c-96dc39d.kyma.ondemand.com/api/import/perf_test_10k" \
  -H "X-API-Key: demo-test-key-for-development-only" \
  -H "X-Auth-Email: perf@test.com" \
  -F "file=@test_10k_products.csv" \
  --max-time 120

# Várható: ~3-5 sec, 10000 processed_rows ✅
```

## 🔍 6. Troubleshooting

### Probléma: Még mindig 0 processed_rows

```bash
# Ellenőrizd az image verzióját
kubectl describe pod -l app=btppg-driver | grep Image:

# Ha még a régi image (clean-v1):
kubectl set image deployment/btppg-driver btppg-driver=fritzgy/btppg-driver:v2-apikey
kubectl rollout status deployment/btppg-driver
```

### Probléma: "Missing API Key"

```bash
# Ellenőrizd a secret-et
kubectl get secret btppg-api-keys

# Ha nincs:
kubectl apply -f api-keys-secret.yaml
kubectl rollout restart deployment/btppg-driver
```

### Probléma: Pod nem indul

```bash
# Logs
kubectl logs -l app=btppg-driver

# Describe
kubectl describe pod -l app=btppg-driver

# Gyakori ok: secret missing, image pull error
```

## ✅ 7. Sikeres Deployment Checklist

- [ ] Docker image built és pushed
- [ ] btppg-api-keys secret created
- [ ] Deployment updated to v2-apikey image
- [ ] Pods running (kubectl get pods)
- [ ] Health check OK
- [ ] CSV import teszt: processed_rows > 0
- [ ] Performance teszt: 10K < 10 sec

## 🎯 Következő Lépések

1. ✅ Dokumentáld az API key-ket tenant-enként
2. ✅ Állíts be monitoring/alerting-et
3. ✅ Konfiguráld a BTP Destination-öket
4. ✅ Teszteld prod-szerű adatokkal
5. ✅ Key rotation folyamat tesztelése
