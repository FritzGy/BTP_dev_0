#!/bin/bash
# Neon PostgreSQL közvetlen teszt (ha van psql)

DB_URL="postgresql://neondb_owner:npg_jL7BwRrqmnC3@ep-falling-truth-add5709i-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"

echo "=== Neon PostgreSQL Health Check ==="
echo "Host: ep-falling-truth-add5709i-pooler.c-2.us-east-1.aws.neon.tech"
echo "Database: neondb"
echo "Provider: Neon (pooled connection)"
echo ""

if command -v psql &> /dev/null; then
    echo "✅ psql found, testing connection..."
    psql "$DB_URL" -c "SELECT version(), current_database(), current_user, now();" -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
else
    echo "⚠️  psql not found. Install: sudo apt-get install postgresql-client"
    echo ""
    echo "Alternative: Test via Python (requires psycopg2):"
    echo "  pip install psycopg2-binary"
    echo "  python3 NEON_DB_DIRECT_TEST.py"
fi
