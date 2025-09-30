from flask import Blueprint, request, jsonify
from services.import_service import ImportService
from services.database_service import DatabaseService
from services.apikey_service import require_flexible_auth
import logging

logger = logging.getLogger(__name__)

import_bp = Blueprint('import', __name__, url_prefix='/api/import')

def get_import_service():
    """Import service lekérése"""
    from flask import current_app
    db_service = DatabaseService(current_app.db_manager)
    return ImportService(db_service)

@import_bp.route('/<table_name>', methods=['POST'])
@require_flexible_auth  # API Key VAGY OAuth2 auth
def import_file(table_name):
    """
    Fájl import endpoint - SAP BTP Destination kompatibilis

    Authentication módok:
    1. X-API-Key header (ajánlott batch importhoz)
    2. Basic Authentication (SAP BTP Destination)
    3. Bearer token (OAuth2 backward compatibility)

    SAP BTP Destination példa:
    - Type: HTTP
    - Authentication: NoAuthentication (ha X-API-Key header-t használsz)
      VAGY BasicAuthentication (user: api-key, password: <your-key>)
    - Additional Properties: X-API-Key=<your-api-key>
    """
    # Tenant info automatikusan beállítva az auth decorator által
    tenant = getattr(request, 'tenant', 'unknown')
    auth_method = getattr(request, 'auth_method', 'unknown')

    logger.info(f"Import request - Tenant: {tenant}, Auth: {auth_method}")

    # Auth email lekérése (header vagy form data)
    auth_email = request.headers.get('X-Auth-Email') or request.form.get('auth_email')
    if not auth_email:
        return jsonify({'status': 'error', 'message': 'X-Auth-Email header required'}), 400
    
    # Fájl ellenőrzése
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400
    
    # Fájl olvasása
    file_content = file.read()
    filename = file.filename
    
    # Import service használata
    import_service = get_import_service()
    result = import_service.import_file(file_content, filename, table_name, auth_email)

    # Tenant és auth method info hozzáadása
    result['tenant'] = tenant
    result['auth_method'] = auth_method

    status_code = 200 if result['status'] == 'success' else 400
    return jsonify(result), status_code

@import_bp.route('/log', methods=['GET'])
def get_import_log():
    """Import log lekérése"""
    limit = int(request.args.get('limit', 100))
    import_service = get_import_service()
    log = import_service.get_import_log(limit)
    
    return jsonify({'status': 'success', 'log': log})

