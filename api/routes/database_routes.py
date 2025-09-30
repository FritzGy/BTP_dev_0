from flask import Blueprint, jsonify, request
from services.database_service import DatabaseService
from services.security_service import SecurityService
from services.auth_service import require_oauth2_client_credentials

database_bp = Blueprint('database', __name__, url_prefix='/api')

def get_db_service():
    """Database service lekérése a Flask app context-ből"""
    from flask import current_app
    return DatabaseService(current_app.db_manager)

@database_bp.route('/tables', methods=['GET'])
@require_oauth2_client_credentials
def list_tables():
    """Összes tábla listázása - OAuth2 védett"""
    # User email ellenőrzése
    auth_email = request.headers.get('X-Auth-Email')
    if not auth_email:
        return jsonify({'error': 'X-Auth-Email header required'}), 400
        
    # Tenant info
    tenant = getattr(request, 'oauth_tenant', 'unknown')
    client_id = getattr(request, 'oauth_client_id', 'unknown')
    
    db_service = get_db_service()
    tables = db_service.list_tables()
    
    return jsonify({
        'status': 'success', 
        'tables': tables,
        'tenant': tenant,
        'authenticated_user': auth_email
    })

@database_bp.route('/tables/<table_name>/schema', methods=['GET'])
@require_oauth2_client_credentials
def get_table_schema(table_name):
    """Tábla séma lekérése biztonsági ellenőrzéssel - OAuth2 védett"""
    # User email ellenőrzése
    auth_email = request.headers.get('X-Auth-Email')
    if not auth_email:
        return jsonify({'error': 'X-Auth-Email header required'}), 400
        
    security_service = SecurityService()
    
    # Tábla név validálása
    if not security_service.validate_table_name(table_name):
        return jsonify({
            'status': 'error', 
            'message': 'Invalid table name'
        }), 400
    
    # Tenant info
    tenant = getattr(request, 'oauth_tenant', 'unknown')
    
    db_service = get_db_service()
    schema = db_service.get_table_schema(table_name)
    
    return jsonify({
        'status': 'success', 
        'table': table_name, 
        'schema': schema,
        'tenant': tenant
    })

@database_bp.route('/tables/<table_name>/records', methods=['GET'])
@require_oauth2_client_credentials
def get_records(table_name):
    """Rekordok lekérése biztonsági ellenőrzéssel - OAuth2 védett"""
    # User email ellenőrzése
    auth_email = request.headers.get('X-Auth-Email')
    if not auth_email:
        return jsonify({'error': 'X-Auth-Email header required'}), 400
        
    security_service = SecurityService()
    
    # Tábla név validálása
    if not security_service.validate_table_name(table_name):
        return jsonify({
            'status': 'error', 
            'message': 'Invalid table name'
        }), 400
    
    db_service = get_db_service()
    
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    email_filter = request.args.get('email')
    
    # Email filter validálása ha van
    if email_filter and not security_service.validate_email(email_filter):
        return jsonify({
            'status': 'error',
            'message': 'Invalid email filter'
        }), 400
    
    # Tenant info
    tenant = getattr(request, 'oauth_tenant', 'unknown')
    
    records = db_service.get_records(table_name, limit, offset, email_filter)
    count = db_service.count_records(table_name, email_filter)
    
    return jsonify({
        'status': 'success',
        'table': table_name,
        'records': records,
        'total': count,
        'limit': limit,
        'offset': offset,
        'tenant': tenant,
        'authenticated_user': auth_email
    })

@database_bp.route('/tables/<table_name>/truncate', methods=['DELETE'])
@require_oauth2_client_credentials
def truncate_table(table_name):
    """Tábla összes rekordjának törlése biztonsági ellenőrzéssel - OAuth2 védett"""
    # User email ellenőrzése
    auth_email = request.headers.get('X-Auth-Email')
    if not auth_email:
        return jsonify({'error': 'X-Auth-Email header required'}), 400
        
    security_service = SecurityService()
    
    # Tábla név validálása
    if not security_service.validate_table_name(table_name):
        return jsonify({
            'status': 'error', 
            'message': 'Invalid table name'
        }), 400
    
    # Tenant info
    tenant = getattr(request, 'oauth_tenant', 'unknown')
    
    db_service = get_db_service()
    success = db_service.truncate_table(table_name)
    
    return jsonify({
        'status': 'success' if success else 'error',
        'message': f'Table {table_name} truncated' if success else f'Failed to truncate table {table_name}',
        'tenant': tenant,
        'authenticated_user': auth_email
    })