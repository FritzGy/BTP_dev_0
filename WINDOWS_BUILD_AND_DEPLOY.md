# 🪟 Windows Build & Deploy Útmutató

## 📋 Előfeltételek Windows-on

- ✅ Docker Desktop telepítve és futó
- ✅ Git Bash vagy PowerShell
- ✅ Docker Hub account (fritzgy)
- ✅ Kubectl telepítve
- ✅ kubectl-oidc_login telepítve

## 🚀 1. Projekt Szinkronizálás

### Windows-on (Git Bash vagy PowerShell):

```bash
# Ha még nincs letöltve
cd C:\Projects
git clone <your-repo-url> btppg-driver-kyma0

# Vagy sync a WSL-ről
# Másold át a módosított fájlokat WSL-ről Windows-ra
# WSL path: \\wsl$\Ubuntu\home\gyorgy\Projects\btppg-driver-kyma0
```

## 🐳 2. Docker Build (Windows)

```powershell
# Navigate to project
cd C:\Projects\btppg-driver-kyma0

# Check Docker is running
docker version

# Login to Docker Hub
docker login
# Username: fritzgy
# Password: <your-docker-hub-token>

# Build image (multi-tag)
docker build -t fritzgy/btppg-driver:v2-apikey -t fritzgy/btppg-driver:latest .

# Verify image
docker images | findstr btppg-driver

# Expected output:
# fritzgy/btppg-driver   v2-apikey   <image-id>   <size>
# fritzgy/btppg-driver   latest      <image-id>   <size>
```

**Build time várható:** ~2-3 perc

## 📤 3. Docker Push

```powershell
# Push versioned image
docker push fritzgy/btppg-driver:v2-apikey

# Push latest
docker push fritzgy/btppg-driver:latest

# Verify on Docker Hub
# https://hub.docker.com/repository/docker/fritzgy/btppg-driver/general
```

**Push time várható:** ~1-2 perc (függ a kapcsolattól)

## ☁️ 4. Kyma Deployment (Windows PowerShell vagy Git Bash)

### A) Bejelentkezés Kyma-ba (böngésző szükséges!):

```powershell
# Set kubeconfig
$env:KUBECONFIG = "C:\Projects\btppg-driver-kyma0\kubeconfig.yaml"

# Test connection (böngészőt fog megnyitni a login-hoz!)
kubectl cluster-info

# Login a böngészőben SAP BTP credentials-ekkel
# Visszatér a terminal-ba

# Verify connection
kubectl get nodes
```

### B) API Keys Secret létrehozása:

```powershell
# Create secret YAML
@"
apiVersion: v1
kind: Secret
metadata:
  name: btppg-api-keys
  namespace: default
type: Opaque
stringData:
  API_KEY_DEMO_TEST: "demo-test-key-for-development-only"
  API_KEY_CUSTOMER1_PROD: "customer1-prod-abc123def456ghi789jkl012"
"@ | Out-File -FilePath api-keys-secret.yaml -Encoding UTF8

# Apply secret
kubectl apply -f api-keys-secret.yaml

# Verify
kubectl get secret btppg-api-keys
```

### C) Deployment Update:

```powershell
# Check current deployment
kubectl get deployment btppg-driver

# Update image to new version
kubectl set image deployment/btppg-driver btppg-driver=fritzgy/btppg-driver:v2-apikey

# Watch rollout
kubectl rollout status deployment/btppg-driver

# Expected output:
# Waiting for deployment "btppg-driver" rollout to finish: 1 old replicas are pending termination...
# deployment "btppg-driver" successfully rolled out
```

**Deployment time:** ~30-60 sec

### D) Verify Deployment:

```powershell
# Check pods
kubectl get pods -l app=btppg-driver

# Expected output:
# NAME                            READY   STATUS    RESTARTS   AGE
# btppg-driver-xxxxxxxxx-xxxxx    1/1     Running   0          1m

# Check image version
kubectl describe pod -l app=btppg-driver | findstr Image:

# Expected:
# Image: fritzgy/btppg-driver:v2-apikey

# Check logs
kubectl logs -l app=btppg-driver --tail=50
```

## 🧪 5. Testing (Windows PowerShell)

### Health Check:

```powershell
curl https://btppg-btp.c-96dc39d.kyma.ondemand.com/health
```

**Expected:**
```json
{
  "database": "connected",
  "service": "btppg-driver",
  "status": "healthy",
  "version": "1.0.0"
}
```

### CSV Import Test (2 records):

```powershell
curl -X POST "https://btppg-btp.c-96dc39d.kyma.ondemand.com/api/import/test_v2_windows" `
  -H "X-API-Key: demo-test-key-for-development-only" `
  -H "X-Auth-Email: windows@test.com" `
  -F "file=@test_import.csv"
```

**Expected SUCCESS:**
```json
{
  "status": "success",
  "total_rows": 2,
  "processed_rows": 2,  // ✅ NEM 0!
  "skipped_rows": 0,
  "performance": {
    "execution_time_seconds": 0.15,
    "records_per_second": 13.3
  },
  "tenant": "demo",
  "auth_method": "api_key"
}
```

### Performance Test (10K records):

```powershell
# Measure time
Measure-Command {
  curl -X POST "https://btppg-btp.c-96dc39d.kyma.ondemand.com/api/import/perf_test_10k" `
    -H "X-API-Key: demo-test-key-for-development-only" `
    -H "X-Auth-Email: perf@test.com" `
    -F "file=@test_10k_products.csv" `
    --max-time 120
}
```

**Expected:** ~3-5 sec, 10000 processed_rows ✅

## 🔧 6. Troubleshooting (Windows)

### Docker Build hibák:

```powershell
# Check Docker is running
docker info

# If not running:
# Start Docker Desktop manually

# Clean build cache if needed
docker builder prune
```

### kubectl hibák (OIDC login):

```powershell
# If "executable kubectl-oidc_login not found":

# Install via Chocolatey
choco install kubelogin

# Or download manually:
# https://github.com/int128/kubelogin/releases
# Extract to C:\Program Files\kubectl-oidc_login.exe
# Add to PATH
```

### Pod nem indul:

```powershell
# Check pod status
kubectl describe pod -l app=btppg-driver

# Common issues:
# - ImagePullBackOff: Check image name/tag
# - CrashLoopBackOff: Check logs
# - Pending: Check resources

# Check logs
kubectl logs -l app=btppg-driver --previous
```

### Import még mindig 0 processed_rows:

```powershell
# 1. Verify image version
kubectl get pod -l app=btppg-driver -o jsonpath='{.items[0].spec.containers[0].image}'

# Should be: fritzgy/btppg-driver:v2-apikey

# 2. Check secret exists
kubectl get secret btppg-api-keys -o yaml

# 3. Force restart
kubectl rollout restart deployment/btppg-driver
kubectl rollout status deployment/btppg-driver

# 4. Check logs for API key loading
kubectl logs -l app=btppg-driver | findstr "API key"
```

## ✅ 7. Success Checklist

- [ ] Docker build success
- [ ] Docker push success (check Docker Hub)
- [ ] Kubectl login success (browser opened)
- [ ] btppg-api-keys secret created
- [ ] Deployment updated to v2-apikey
- [ ] Pod running (1/1 Ready)
- [ ] Health check returns "healthy"
- [ ] CSV import test: processed_rows = 2 ✅
- [ ] Performance test: < 10 sec ✅

## 📊 8. Quick Commands Summary

```powershell
# Full deployment sequence (copy-paste)
$env:KUBECONFIG = "C:\Projects\btppg-driver-kyma0\kubeconfig.yaml"

# Build & Push
docker build -t fritzgy/btppg-driver:v2-apikey -t fritzgy/btppg-driver:latest .
docker push fritzgy/btppg-driver:v2-apikey
docker push fritzgy/btppg-driver:latest

# Deploy (after kubectl login)
kubectl apply -f api-keys-secret.yaml
kubectl set image deployment/btppg-driver btppg-driver=fritzgy/btppg-driver:v2-apikey
kubectl rollout status deployment/btppg-driver

# Test
curl https://btppg-btp.c-96dc39d.kyma.ondemand.com/health
curl -X POST "https://btppg-btp.c-96dc39d.kyma.ondemand.com/api/import/test_v2" `
  -H "X-API-Key: demo-test-key-for-development-only" `
  -H "X-Auth-Email: test@demo.com" `
  -F "file=@test_import.csv"
```

## 🎯 Expected Timeline

| Step | Time |
|------|------|
| Docker build | 2-3 min |
| Docker push | 1-2 min |
| kubectl login | 1-2 min (browser) |
| Secret apply | 5 sec |
| Deployment update | 30-60 sec |
| Testing | 1-2 min |
| **TOTAL** | **~7-10 min** |

## 📞 Ha elakadtál:

1. **Check Docker Hub**: https://hub.docker.com/repository/docker/fritzgy/btppg-driver/tags
   - Van v2-apikey tag? ✅
   
2. **Check Kyma Pod**:
   ```powershell
   kubectl get pods -l app=btppg-driver
   kubectl logs -l app=btppg-driver --tail=100
   ```

3. **Check Image in Pod**:
   ```powershell
   kubectl describe pod -l app=btppg-driver | findstr Image:
   ```

Minden sikereket! 🚀
