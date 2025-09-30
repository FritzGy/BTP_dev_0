import psycopg2
import csv
import time
from datetime import datetime
import uuid

# Connection
conn_string = open('/home/fater/btppg-driver-kyma0/Neon_connection_string.txt').read().strip()
conn = psycopg2.connect(conn_string)
cur = conn.cursor()

print("Testing batch insert performance...")

# Truncate
cur.execute("TRUNCATE TABLE products_csv RESTART IDENTITY")
conn.commit()
print("Table truncated")

# Read 1000 rows from CSV
rows = []
with open('/home/fater/btppg-driver-kyma0/test_10k_products.csv', 'r') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= 1000:
            break
        rows.append(row)

print(f"Loaded {len(rows)} rows from CSV")

# Prepare batch data
batch_data = []
for row in rows:
    batch_data.append((
        str(uuid.uuid4()),
        datetime.now(), 
        datetime.now(),
        'batch-test@demo.com',
        row.get('name', ''),
        float(row.get('price', 0)),
        row.get('category', ''),
        row.get('description', ''),
        int(row.get('stock', 0))
    ))

# Batch insert
start = time.time()
cur.executemany("""
    INSERT INTO products_csv (id, created_at, updated_at, auth_email, name, price, category, description, stock)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
""", batch_data)
conn.commit()
duration = time.time() - start

print(f"Inserted {len(batch_data)} records in {duration:.2f} seconds")
print(f"Speed: {len(batch_data)/duration:.0f} records/second")

# Verify
cur.execute("SELECT COUNT(*) FROM products_csv")
count = cur.fetchone()[0]
print(f"Total in table: {count}")

cur.close()
conn.close()
