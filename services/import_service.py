# services/import_service.py - Phase 3: Full Bulk Operations (INSERT + UPDATE)

import logging
import pandas as pd
import numpy as np
import json
import tempfile
import os
import time
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from services.database_service import DatabaseService
from services.security_service import SecurityService

logger = logging.getLogger(__name__)

class ImportService:
    """Enhanced Import Service with CSV, Excel, JSON support and PHASE 3 FULL BULK OPTIMIZATIONS"""

    # Supported file formats
    SUPPORTED_FORMATS = {
        '.csv': 'csv',
        '.xlsx': 'excel',
        '.xls': 'excel',
        '.json': 'json'
    }

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.security_service = SecurityService()
        self.import_log = []

    def import_file(self, file_content: bytes, filename: str, table_name: str, auth_email: str) -> Dict[str, Any]:
        """Universal file import dispatcher"""
        try:
            file_extension = Path(filename).suffix.lower()

            if file_extension not in self.SUPPORTED_FORMATS:
                return self._error_response(
                    f"Unsupported file type: {file_extension}. "
                    f"Supported: {', '.join(self.SUPPORTED_FORMATS.keys())}"
                )

            format_type = self.SUPPORTED_FORMATS[file_extension]

            with tempfile.NamedTemporaryFile(mode='wb', suffix=file_extension, delete=False) as tmp_file:
                tmp_file.write(file_content)
                temp_path = tmp_file.name

            try:
                if format_type == 'csv':
                    result = self._import_csv(temp_path, table_name, auth_email)
                elif format_type == 'excel':
                    result = self._import_excel(temp_path, table_name, auth_email)
                elif format_type == 'json':
                    result = self._import_json(temp_path, table_name, auth_email)
                else:
                    result = self._error_response(f"Import handler missing: {format_type}")

                result["source_format"] = format_type
                return result

            finally:
                try:
                    os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Temp file cleanup error: {cleanup_error}")

        except Exception as e:
            logger.error(f"Import file error ({filename}): {e}")
            return self._error_response(f"File processing error: {str(e)}")

    def import_csv(self, file_path: str, table_name: str, auth_email: str) -> Dict[str, Any]:
        """CSV import - backward compatibility"""
        result = self._import_csv(file_path, table_name, auth_email)
        result["source_format"] = "csv"
        return result

    def _import_csv(self, file_path: str, table_name: str, auth_email: str) -> Dict[str, Any]:
        """CSV file import"""
        try:
            logger.info(f"CSV import: {file_path} -> {table_name}")
            df = pd.read_csv(file_path)
            return self._process_dataframe_import(df, table_name, auth_email, "CSV")
        except Exception as e:
            logger.error(f"CSV import error: {e}")
            return self._error_response(f"CSV import error: {str(e)}")

    def _import_excel(self, file_path: str, table_name: str, auth_email: str) -> Dict[str, Any]:
        """Excel file import"""
        try:
            logger.info(f"Excel import: {file_path} -> {table_name}")
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
            except ImportError:
                return self._error_response("Excel support requires: pip install openpyxl")
            return self._process_dataframe_import(df, table_name, auth_email, "Excel")
        except Exception as e:
            logger.error(f"Excel import error: {e}")
            return self._error_response(f"Excel import error: {str(e)}")

    def _import_json(self, file_path: str, table_name: str, auth_email: str) -> Dict[str, Any]:
        """JSON file import"""
        try:
            logger.info(f"JSON import: {file_path} -> {table_name}")
            df = pd.read_json(file_path)
            return self._process_dataframe_import(df, table_name, auth_email, "JSON")
        except Exception as e:
            logger.error(f"JSON import error: {e}")
            return self._error_response(f"JSON import error: {str(e)}")

    def _process_dataframe_import(self, df: pd.DataFrame, table_name: str, auth_email: str, format_name: str) -> Dict[str, Any]:
        """Common DataFrame processing logic for all formats"""
        if df.empty:
            return self._error_response(f"The {format_name} file is empty or contains no data")

        logger.info(f"{format_name} processing: {len(df)} rows, columns: {list(df.columns)}")

        df = self._clean_dataframe_nan_values(df)
        self._ensure_table_with_columns(table_name, df.columns.tolist(), auth_email)
        
        # PHASE 3 OPTIMIZATION: Use full bulk processing
        return self._process_dataframe_records_phase3_full_bulk(df, table_name, auth_email)

    def _clean_dataframe_nan_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean DataFrame NaN and empty values in UUID column"""
        if 'id' not in df.columns:
            return df

        logger.debug(f"UUID column before cleaning: {df['id'].tolist()}")

        df['id'] = df['id'].replace('nan', None)
        df['id'] = df['id'].replace({np.nan: None})
        df['id'] = df['id'].where(df['id'].notna(), None)

        def normalize_uuid_value(value):
            if pd.isna(value) or value is None:
                return None
            str_value = str(value).strip().lower()
            if str_value in ['nan', '', 'none', 'null', 'na']:
                return None
            if not str_value:
                return None
            return str(value).strip() if str(value).strip() else None

        df['id'] = df['id'].apply(normalize_uuid_value)
        logger.debug(f"UUID column after cleaning: {df['id'].tolist()}")
        return df

    def _ensure_table_with_columns(self, table_name: str, columns: List[str], auth_email: str):
        """Ensure table structure with dynamic column addition"""
        if not self.db_service.table_exists(table_name):
            logger.info(f"Creating new table: {table_name}")
            table_columns = {
                'id': 'UUID PRIMARY KEY DEFAULT gen_random_uuid()',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'auth_email': 'VARCHAR(255) NOT NULL'
            }

            for col in columns:
                if col.lower() != 'id':
                    table_columns[col] = self._determine_column_type(col)

            self.db_service.create_table(table_name, table_columns)
        else:
            existing_schema = self.db_service.get_table_schema(table_name)
            existing_columns = [col['column_name'] for col in existing_schema]

            for col in columns:
                if col not in existing_columns and col.lower() != 'id':
                    column_type = self._determine_column_type(col)
                    logger.info(f"Adding new column: {col} ({column_type}) -> {table_name}")
                    self.db_service.add_column(table_name, col, column_type)

    def _determine_column_type(self, column_name: str) -> str:
        """Determine column type based on name"""
        column_lower = column_name.lower()
        if any(keyword in column_lower for keyword in ['price', 'cost', 'amount', 'total']):
            return 'NUMERIC'
        elif any(keyword in column_lower for keyword in ['stock', 'quantity', 'count', 'number']):
            return 'INTEGER'
        elif any(keyword in column_lower for keyword in ['date', 'time', 'created', 'updated']):
            return 'TIMESTAMP'
        elif any(keyword in column_lower for keyword in ['email', 'url', 'phone']):
            return 'VARCHAR(255)'
        else:
            return 'TEXT'

    def _process_dataframe_records_phase3_full_bulk(self, df: pd.DataFrame, table_name: str, auth_email: str) -> Dict[str, Any]:
        """
        PHASE 3 OPTIMALIZÁCIÓ: Bulk UUID check + Bulk INSERT + Bulk UPDATE
        Teljes bulk processing - minden művelet optimalizált
        """
        start_time = time.time()
        total_rows = len(df)
        has_uuid_column = 'id' in df.columns

        logger.info(f"PHASE 3: Starting full bulk operations for {total_rows} records")

        # PHASE 1: Bulk UUID existence check
        uuid_existence_map = {}
        if has_uuid_column:
            uuid_existence_map = self._bulk_uuid_existence_check(df, table_name)

        # PHASE 2 & 3: Separate records into batches
        insert_records = []
        update_records = []
        dropped_uuids = []
        warnings = []
        errors = []

        for index, row in df.iterrows():
            try:
                row_data = row.to_dict()
                uuid_action = self._determine_uuid_action_with_bulk_lookup(
                    row_data, table_name, has_uuid_column, uuid_existence_map
                )

                if uuid_action['action'] == 'drop':
                    dropped_uuids.append(uuid_action['uuid'])
                    warnings.append(f"Row {index + 1}: UUID not found in database, dropped")
                elif uuid_action['action'] == 'insert':
                    insert_data = self._prepare_insert_data(row_data)
                    if insert_data:
                        insert_records.append({'data': insert_data, 'row_index': index})
                    else:
                        warnings.append(f"Row {index + 1}: No valid data to insert")
                elif uuid_action['action'] == 'update':
                    update_data = self._prepare_update_data(row_data)
                    if update_data:
                        update_records.append({
                            'uuid': uuid_action['uuid'],
                            'data': update_data,
                            'row_index': index
                        })
                    else:
                        warnings.append(f"Row {index + 1}: No valid data to update")
            except Exception as e:
                logger.error(f"Row processing error (index: {index}): {e}")
                errors.append(f"Row {index + 1}: Processing error - {str(e)}")

        # PHASE 2: Execute bulk INSERT
        insert_success_count = 0
        if insert_records:
            bulk_insert_start = time.time()
            insert_success_count = self._execute_bulk_insert_phase2(table_name, insert_records, auth_email)
            bulk_insert_time = time.time() - bulk_insert_start
            logger.info(f"PHASE 2: Bulk INSERT completed in {bulk_insert_time:.2f}s")
            logger.info(f"Successfully inserted {insert_success_count}/{len(insert_records)} records")

        # PHASE 3: Execute bulk UPDATE
        update_success_count = 0
        if update_records:
            bulk_update_start = time.time()
            update_success_count = self._execute_bulk_update_phase3(table_name, update_records, auth_email)
            bulk_update_time = time.time() - bulk_update_start
            logger.info(f"PHASE 3: Bulk UPDATE completed in {bulk_update_time:.2f}s")
            logger.info(f"Successfully updated {update_success_count}/{len(update_records)} records")

        processed_rows = insert_success_count + update_success_count
        skipped_rows = total_rows - processed_rows
        execution_time = time.time() - start_time

        # Status determination
        if processed_rows > 0:
            status = "success"
        elif dropped_uuids or warnings:
            status = "warning"
        else:
            status = "error"

        return {
            "status": status,
            "total_rows": total_rows,
            "processed_rows": processed_rows,
            "skipped_rows": skipped_rows,
            "dropped_uuids": dropped_uuids,
            "warnings": warnings,
            "errors": errors,
            "performance": {
                "execution_time_seconds": round(execution_time, 2),
                "records_per_second": round(processed_rows / execution_time if execution_time > 0 else 0, 1),
                "optimization_phase": "phase_3_full_bulk",
                "uuid_bulk_check_enabled": len(uuid_existence_map) > 0,
                "bulk_insert_count": insert_success_count,
                "bulk_update_count": update_success_count,
                "bulk_operations_used": (insert_success_count > 0 or update_success_count > 0)
            }
        }

    def _bulk_uuid_existence_check(self, df: pd.DataFrame, table_name: str) -> Dict[str, bool]:
        """PHASE 1: Bulk UUID existence check"""
        logger.info("PHASE 1: Starting bulk UUID existence check...")
        uuid_existence_map = {}

        valid_uuids = []
        for uuid_val in df['id']:
            if pd.notna(uuid_val):
                uuid_str = str(uuid_val).strip()
                if self._is_valid_uuid_format(uuid_str):
                    valid_uuids.append(uuid_str)

        if valid_uuids:
            uuid_check_start = time.time()
            try:
                placeholders = ','.join(['%s'] * len(valid_uuids))
                check_query = f"SELECT id FROM {table_name} WHERE id IN ({placeholders})"

                existing_records = self.db_service.db_manager.execute_query(check_query, valid_uuids)
                existing_uuids = {record['id'] for record in existing_records} if existing_records else set()

                for uuid in valid_uuids:
                    uuid_existence_map[uuid] = uuid in existing_uuids

                uuid_check_time = time.time() - uuid_check_start
                logger.info(f"PHASE 1: Bulk UUID check completed in {uuid_check_time:.2f}s")
                logger.info(f"Found {len(existing_uuids)} existing UUIDs out of {len(valid_uuids)} checked")

            except Exception as e:
                logger.error(f"Bulk UUID check failed: {e}, falling back to individual checks")
                uuid_existence_map = {}

        return uuid_existence_map

    def _execute_bulk_insert_phase2(self, table_name: str, insert_records: List[Dict], auth_email: str) -> int:
        """PHASE 2: Execute bulk INSERT using VALUES clause"""
        if not insert_records:
            return 0

        try:
            current_time = datetime.now()

            # Determine columns from first record
            sample_data = insert_records[0]['data']
            data_columns = list(sample_data.keys())
            all_columns = ['id'] + data_columns + ['created_at', 'updated_at', 'auth_email']

            # Build VALUES clause for bulk INSERT
            values_parts = []
            params = []

            for record in insert_records:
                # ID (auto-generated)
                params.append(str(uuid4()))

                # Data columns
                for col in data_columns:
                    value = record['data'].get(col)
                    params.append(value if value is not None else None)

                # Audit columns
                params.extend([current_time, current_time, auth_email])

                # Create placeholder
                placeholders = ','.join(['%s'] * len(all_columns))
                values_parts.append(f"({placeholders})")

            # Build and execute bulk INSERT
            columns_clause = ','.join(all_columns)
            values_clause = ','.join(values_parts)

            insert_sql = f"""
                INSERT INTO {table_name} ({columns_clause})
                VALUES {values_clause}
            """

            logger.debug(f"Bulk INSERT SQL: {len(insert_records)} records")
            self.db_service.db_manager.execute_query(insert_sql, params, fetch=False)

            return len(insert_records)

        except Exception as e:
            logger.error(f"Bulk INSERT failed: {e}")

            # Fallback to individual inserts
            logger.info("Falling back to individual INSERT operations")
            success_count = 0
            for record in insert_records:
                try:
                    result_uuid = self.db_service.insert_record(table_name, record['data'], auth_email)
                    if result_uuid:
                        success_count += 1
                except Exception as individual_error:
                    logger.error(f"Individual INSERT also failed: {individual_error}")

            return success_count

    def _execute_bulk_update_phase3(self, table_name: str, update_records: List[Dict], auth_email: str) -> int:
        """
        PHASE 3: Execute bulk UPDATE using CASE statements
        Sokkal gyorsabb mint egyenként UPDATE-elni
        """
        if not update_records:
            return 0

        try:
            current_time = datetime.now()

            # Determine all unique data columns across all records
            all_data_columns = set()
            for record in update_records:
                all_data_columns.update(record['data'].keys())

            all_data_columns = sorted(list(all_data_columns))

            # Build CASE statements for each column
            set_clauses = []
            params = []

            for column in all_data_columns:
                case_parts = []
                for record in update_records:
                    if column in record['data']:
                        case_parts.append("WHEN id = %s THEN %s")
                        params.extend([record['uuid'], record['data'][column]])

                if case_parts:
                    case_stmt = f"""
                        {column} = CASE
                            {' '.join(case_parts)}
                            ELSE {column}
                        END
                    """
                    set_clauses.append(case_stmt)

            # Add audit column updates
            set_clauses.append("updated_at = %s")
            set_clauses.append("auth_email = %s")
            params.extend([current_time, auth_email])

            # WHERE clause with all UUIDs
            update_uuids = [record['uuid'] for record in update_records]
            where_placeholders = ','.join(['%s'] * len(update_uuids))
            params.extend(update_uuids)

            # Build and execute bulk UPDATE
            set_clause = ', '.join(set_clauses)
            update_sql = f"""
                UPDATE {table_name} 
                SET {set_clause}
                WHERE id IN ({where_placeholders})
            """

            logger.debug(f"Bulk UPDATE SQL: {len(update_records)} records")
            self.db_service.db_manager.execute_query(update_sql, params, fetch=False)

            return len(update_records)

        except Exception as e:
            logger.error(f"Bulk UPDATE failed: {e}")

            # Fallback to individual updates
            logger.info("Falling back to individual UPDATE operations")
            success_count = 0
            for record in update_records:
                try:
                    success = self.db_service.update_record(
                        table_name,
                        record['uuid'], 
                        record['data'],
                        auth_email
                    )
                    if success:
                        success_count += 1
                except Exception as individual_error:
                    logger.error(f"Individual UPDATE also failed: {individual_error}")

            return success_count

    def _determine_uuid_action_with_bulk_lookup(self, row_data: Dict[str, Any], table_name: str,
                                               has_uuid_column: bool, uuid_existence_map: Dict[str, bool]) -> Dict[str, Any]:
        """Enhanced UUID action determination with bulk lookup"""
        if not has_uuid_column or not row_data.get('id'):
            return {'action': 'insert', 'uuid': None, 'reason': 'No UUID provided - will auto-generate'}

        provided_uuid = str(row_data['id']).strip()

        if not self._is_valid_uuid_format(provided_uuid):
            return {'action': 'drop', 'uuid': provided_uuid, 'reason': 'Invalid UUID format'}

        # Fast lookup using pre-computed map
        if provided_uuid in uuid_existence_map:
            if uuid_existence_map[provided_uuid]:
                return {'action': 'update', 'uuid': provided_uuid, 'reason': 'UUID exists - will update record'}
            else:
                return {'action': 'drop', 'uuid': provided_uuid, 'reason': 'UUID not found in database'}
        else:
            # Fallback to individual check
            if self._uuid_exists_in_table(table_name, provided_uuid):
                return {'action': 'update', 'uuid': provided_uuid, 'reason': 'UUID exists - will update record (individual check)'}
            else:
                return {'action': 'drop', 'uuid': provided_uuid, 'reason': 'UUID not found in database (individual check)'}

    def _is_valid_uuid_format(self, uuid_string: str) -> bool:
        """UUID format validation"""
        import uuid as uuid_module
        try:
            uuid_module.UUID(uuid_string)
            return True
        except (ValueError, AttributeError, TypeError):
            return False

    def _uuid_exists_in_table(self, table_name: str, uuid: str) -> bool:
        """Check UUID existence"""
        try:
            query = f"SELECT 1 FROM {table_name} WHERE id = %s LIMIT 1"
            result = self.db_service.db_manager.execute_query(query, (uuid,))
            return len(result) > 0 if result else False
        except Exception as e:
            logger.error(f"UUID existence check error ({table_name}/{uuid}): {e}")
            return False

    def _prepare_insert_data(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for insert"""
        clean_data = {}
        for key, value in row_data.items():
            if key.lower() == 'id':
                continue
            if pd.notna(value) and value is not None:
                if self.security_service.is_safe_value(key, str(value)):
                    clean_data[key] = value
                else:
                    logger.warning(f"Security check failed: {key}={value}")
        return clean_data

    def _prepare_update_data(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for update"""
        return self._prepare_insert_data(row_data)

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Standard error response"""
        return {
            "status": "error",
            "message": message,
            "total_rows": 0,
            "processed_rows": 0,
            "skipped_rows": 0,
            "dropped_uuids": [],
            "warnings": [],
            "errors": [message]
        }

    def get_supported_formats(self) -> Dict[str, str]:
        """Get supported file formats"""
        return self.SUPPORTED_FORMATS.copy()