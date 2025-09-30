import psycopg2
import csv
import os
from datetime import datetime
import uuid

# Neon connection string
conn_string = open('/home/fater/btppg-driver-kyma0/Neon_connection_string.txt').read().strip()

# Connect
conn = psycopg2.connect(conn_string)
cur = conn.cursor()

# Truncate first
print("Truncating table...")
cur.execute("TRUNCATE TABLE products_csv RESTART IDENTITY")
conn.commit()

# Read CSV
print("Reading CSV...")
with open('/home/fater/btppg-driver-kyma0/test_10k_products.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    print(f"Found {len(rows)} rows")

# Batch insert
print("Batch inserting...")
start = datetime.now()

values = []
for row in rows:
    values.append((
        str(uuid.uuid4()),
        datetime.now(),
        datetime.now(),
        'batch-import@test.com',
        row.get('name', ''),
        float(row.get('price', 0)),
        row.get('category', ''),
        row.get('description', ''),
        int(row.get('stock', 0))
    ))

# Bulk insert
query = """
INSERT INTO products_csv (id, created_at, updated_at, auth_email, name, price, category, description, stock)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

cur.executemany(query, values)
conn.commit()

end = datetime.now()
duration = (end - start).total_seconds()

print(f"Inserted {len(values)} records in {duration:.2f} seconds")
print(f"Speed: {len(values)/duration:.0f} records/second")

# Verify
cur.execute("SELECT COUNT(*) FROM products_csv")
count = cur.fetchone()[0]
print(f"Total records in table: {count}")

cur.close()
conn.close()
