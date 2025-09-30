from flask import Blueprint, request, jsonify
from services.database_service import DatabaseService
import csv
import io
import time
from datetime import datetime

test_bp = Blueprint('test', __name__, url_prefix='/test')

def get_db_service():
    from flask import current_app
    return DatabaseService(current_app.db_manager)

@test_bp.route('/batch-import/<table_name>', methods=['POST'])
def batch_import_no_auth(table_name):
    """Batch import WITHOUT token authentication for performance testing"""
    start_time = time.time()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    file_content = file.read().decode('utf-8')
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(file_content))
    records = list(csv_reader)
    
    db_service = get_db_service()
    
    # Batch insert - egyesével, de auth check nélkül
    success_count = 0
    for record in records:
        try:
            # Direct insert without token validation
            db_service.insert_record(table_name, record, 'batch-test@noauth.com')
            success_count += 1
        except:
            pass
    
    duration = time.time() - start_time
    
    return jsonify({
        'status': 'success',
        'records_processed': len(records),
        'records_inserted': success_count,
        'duration_seconds': round(duration, 2),
        'records_per_second': round(success_count / duration, 2) if duration > 0 else 0
    })

@test_bp.route('/bulk-insert/<table_name>', methods=['POST'])
def bulk_insert_no_auth(table_name):
    """TRUE bulk insert with executemany for maximum performance"""
    start_time = time.time()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    file_content = file.read().decode('utf-8')
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(file_content))
    records = list(csv_reader)
    
    # Direct database connection for bulk insert
    from flask import current_app
    import uuid
    
    conn = current_app.db_manager._get_connection()
    cursor = conn.cursor()
    
    try:
        # Prepare bulk data
        bulk_data = []
        for record in records:
            bulk_data.append((
                str(uuid.uuid4()),
                datetime.now(),
                datetime.now(),
                'bulk-test@noauth.com',
                record.get('name', ''),
                float(record.get('price', 0)) if record.get('price') else 0,
                record.get('category', ''),
                record.get('description', ''),
                int(record.get('stock', 0)) if record.get('stock') else 0
            ))
        
        # Execute bulk insert
        cursor.executemany("""
            INSERT INTO products_csv 
            (id, created_at, updated_at, auth_email, name, price, category, description, stock)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, bulk_data)
        
        conn.commit()
        inserted_count = cursor.rowcount
        
        duration = time.time() - start_time
        
        return jsonify({
            'status': 'success',
            'records_processed': len(records),
            'records_inserted': inserted_count,
            'duration_seconds': round(duration, 2),
            'records_per_second': round(inserted_count / duration, 2) if duration > 0 else 0
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        current_app.db_manager._put_connection(conn, error=False)
