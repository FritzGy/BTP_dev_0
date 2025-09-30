# btppg-driver Tesztelési Útmutató

## 1. Alkalmazás elérése

### Kyma deployment ellenőrzése
```bash
# Export kubeconfig
export KUBECONFIG=/home/gyorgy/Projects/btppg-driver-kyma0/kubeconfig.yaml

# Deployment státusz
kubectl get deployments -l app=btppg-driver
kubectl get pods -l app=btppg-driver
kubectl get svc btppg-driver

# Logok megtekintése
kubectl logs -l app=btppg-driver --tail=50

# Port forward helyi teszteléshez
kubectl port-forward svc/btppg-driver 8080:80
```

## 2. Health Check Tesztek

### Alkalmazás health (port-forward után)
```bash
# Alapvető health check
curl http://localhost:8080/health

# Részletes státusz
curl http://localhost:8080/api/status

# Főoldal
curl http://localhost:8080/

# Táblák listázása
curl http://localhost:8080/api/tables
```

## 3. CSV Import Teszt

### Kis CSV fájl import (test_import.csv - 2 rekord)
```bash
curl -X POST http://localhost:8080/api/import/test_products \
  -H "X-Auth-Email: test@example.com" \
  -F "file=@test_import.csv"
```

### JSON import teszt
```bash
curl -X POST http://localhost:8080/api/import/test_products_json \
  -H "X-Auth-Email: test@example.com" \
  -F "file=@test_import.json"
```

### Excel import teszt
```bash
curl -X POST http://localhost:8080/api/import/test_products_excel \
  -H "X-Auth-Email: test@example.com" \
  -F "file=@test_import.xlsx"
```

### Nagy CSV fájl (10K rekord - performance teszt)
```bash
curl -X POST http://localhost:8080/api/import/products_csv \
  -H "X-Auth-Email: batch-test@demo.com" \
  -F "file=@test_10k_products.csv" \
  --max-time 120
```

## 4. Neon PostgreSQL Közvetlen Teszt

Ha telepítve van psycopg2:
```bash
python3 << 'PYEOF'
import psycopg2

# Connection string a .env fájlból
db_url = "postgresql://neondb_owner:npg_jL7BwRrqmnC3@ep-falling-truth-add5709i-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Version check
    cur.execute("SELECT version(), current_database()")
    result = cur.fetchone()
    print(f"✅ Connected to: {result[1]}")
    print(f"PostgreSQL: {result[0][:80]}...")
    
    # List tables
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = cur.fetchall()
    print(f"\nTáblák ({len(tables)} db):")
    for t in tables:
        print(f"  - {t[0]}")
    
    cur.close()
    conn.close()
    print("\n✅ Connection test successful")
    
except Exception as e:
    print(f"❌ Error: {e}")
PYEOF
```

## 5. Import Eredmények Ellenőrzése

```bash
# Rekordok száma a táblában
curl -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -H "X-Auth-Email: test@example.com" \
  -d '{"query": "SELECT COUNT(*) as count FROM test_products"}'

# Első 5 rekord
curl -X POST http://localhost:8080/api/query \
  -H "Content-Type: application/json" \
  -H "X-Auth-Email: test@example.com" \
  -d '{"query": "SELECT * FROM test_products LIMIT 5"}'
```

## 6. Várható Eredmények

### Sikeres CSV import (2 rekord):
```json
{
  "status": "success",
  "total_rows": 2,
  "processed_rows": 2,
  "skipped_rows": 0,
  "performance": {
    "execution_time_seconds": 0.15,
    "records_per_second": 13.3,
    "optimization_phase": "phase_3_full_bulk"
  }
}
```

### Sikeres 10K import (várható ~8-10 másodperc):
```json
{
  "status": "success",
  "total_rows": 10000,
  "processed_rows": 10000,
  "performance": {
    "execution_time_seconds": 8.5,
    "records_per_second": 1176.5,
    "bulk_insert_count": 10000
  }
}
```

## 7. Troubleshooting

### Ha nem elérhető az alkalmazás:
```bash
# Ellenőrizd a pod státuszt
kubectl get pods -l app=btppg-driver

# Nézd meg a logokat
kubectl logs -l app=btppg-driver --tail=100

# Restart deployment
kubectl rollout restart deployment/btppg-driver
```

### Ha DB connection error:
- Ellenőrizd a neon-db-secret secret-et
- Nézd meg a logs-ban a connection error üzeneteket
- Teszteld a Neon adatbázist közvetlenül psql-lel
