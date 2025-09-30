import logging
import os
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from typing import Optional, Dict, Any, List
from .config import Config
import time

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Javított PostgreSQL adatbázis kapcsolat kezelő ThreadedConnectionPool-lal Kyma környezethez"""
    
    def __init__(self, config: Optional[Config] = None):
        """DatabaseManager inicializálása"""
        self.config = config or Config()
        self.database_url = self._get_database_url()
        self.pool = None
        self._initialize_pool()
        
        # Connection teszt
        if self.test_connection():
            logger.info("✅ Adatbázis kapcsolat teszt sikeres")
        else:
            logger.error("❌ Adatbázis kapcsolat teszt sikertelen")
    
    def _get_database_url(self) -> str:
        """Database URL lekérése environment változóból"""
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("DATABASE_URL environment változó nincs beállítva")
            raise ValueError("DATABASE_URL environment változó hiányzik")
        
        logger.info(f"Database URL beállítva: {database_url[:30]}...")
        return database_url
    
    def _initialize_pool(self):
        """Connection pool inicializálása Kyma-optimalizált beállításokkal"""
        try:
            # Kyma-barát beállítások
            self.pool = ThreadedConnectionPool(
                minconn=2,          # Minimum connections (alacsonyabb mint korábban)
                maxconn=10,         # Maximum connections (alacsonyabb limit)
                dsn=self.database_url,
                cursor_factory=psycopg2.extras.RealDictCursor,
                # Kyma/Kubernetes specifikus beállítások
                connect_timeout=10,
                application_name="btppg-driver-kyma-pool",
                # Keep-alive beállítások Kubernetes networkinghez
                keepalives_idle=30,     # 30 sec idle után keep-alive
                keepalives_interval=5,  # 5 sec keep-alive intervals  
                keepalives_count=3      # 3 sikertelen után disconnect
            )
            logger.info("✅ ThreadedConnectionPool inicializálva Kyma-optimalizált beállításokkal")
            
        except Exception as e:
            logger.error(f"❌ Connection pool inicializálás hiba: {e}")
            raise
    
    def _get_connection(self):
        """Biztonságos connection lekérése a pool-ból retry logikával"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if not self.pool:
                    logger.warning("Pool nincs inicializálva, újrapróbálkozás...")
                    self._initialize_pool()
                
                conn = self.pool.getconn()
                
                # Connection health check
                if conn.closed != 0:
                    logger.warning(f"Zárt connection észlelve (attempt {attempt + 1}), új connection kérése...")
                    self.pool.putconn(conn, close=True)
                    continue
                
                # Gyors ping teszt
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                
                return conn
                
            except Exception as e:
                logger.warning(f"Connection lekérés hiba (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    # Utolsó kísérlet - pool újrainiticalizálás
                    logger.error("Connection pool újrainiticalizálás szükséges")
                    self._reinitialize_pool()
                    raise
                
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
        
        raise Exception("Connection lekérés sikertelen minden kísérlet után")
    
    def _put_connection(self, conn, error=False):
        """Biztonságos connection visszaadás a pool-ba"""
        try:
            if error or conn.closed != 0:
                # Ha hiba volt vagy a connection zárt, zárjuk le
                self.pool.putconn(conn, close=True)
                logger.debug("Connection lezárva hiba miatt")
            else:
                # Normál visszaadás
                self.pool.putconn(conn)
                logger.debug("Connection visszaadva a pool-ba")
        except Exception as e:
            logger.warning(f"Connection visszaadás hiba: {e}")
    
    def _reinitialize_pool(self):
        """Pool újrainiticializálás kritikus hiba esetén"""
        try:
            if self.pool:
                self.pool.closeall()
                logger.info("Régi pool lezárva")
            
            self._initialize_pool()
            logger.info("Pool újrainiticalizálva")
            
        except Exception as e:
            logger.error(f"Pool újrainiticializálás hiba: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Adatbázis kapcsolat tesztelése"""
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 as test, current_timestamp")
            result = cursor.fetchone()
            cursor.close()
            
            logger.info(f"Kapcsolat teszt sikeres: {result}")
            return True
            
        except Exception as e:
            logger.error(f"Kapcsolat teszt sikertelen: {e}")
            return False
        finally:
            if conn:
                self._put_connection(conn, error=False)
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """SQL lekérdezés végrehajtása javított error handling-gel"""
        conn = None
        cursor = None
        error_occurred = False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Ha SELECT lekérdezés
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
                return [dict(row) for row in result] if result else []
            else:
                # INSERT, UPDATE, DELETE esetén
                conn.commit()
                return []
                
        except psycopg2.InterfaceError as e:
            error_occurred = True
            logger.error(f"Interface hiba (connection issue): {e}")
            # Pool újrainiticializálás szükséges lehet
            raise
            
        except psycopg2.OperationalError as e:
            error_occurred = True
            logger.error(f"Operational hiba (network/db issue): {e}")
            raise
            
        except Exception as e:
            error_occurred = True
            logger.error(f"Query végrehajtás hiba: {e}")
            if conn and conn.closed == 0:
                try:
                    conn.rollback()
                except:
                    pass
            raise
            
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                self._put_connection(conn, error=error_occurred)
    
    def execute_batch(self, query: str, data_list: List[tuple]) -> int:
        """Batch insert optimalizált nagyobb adathalmazokhoz"""
        conn = None
        cursor = None
        error_occurred = False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Batch execute - sokkal gyorsabb mint egyesével
            psycopg2.extras.execute_batch(
                cursor, 
                query, 
                data_list,
                page_size=1000  # 1000 record batch-enként
            )
            
            conn.commit()
            affected_rows = cursor.rowcount
            logger.info(f"Batch execute sikeres: {affected_rows} sor érintett")
            return affected_rows
            
        except Exception as e:
            error_occurred = True
            logger.error(f"Batch execute hiba: {e}")
            if conn and conn.closed == 0:
                try:
                    conn.rollback()
                except:
                    pass
            raise
            
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                self._put_connection(conn, error=error_occurred)
    
    def execute_transaction(self, queries: List[tuple]) -> bool:
        """Tranzakció végrehajtása"""
        conn = None
        cursor = None
        error_occurred = False
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            for query, params in queries:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
            
            conn.commit()
            logger.info(f"Tranzakció sikeres: {len(queries)} query végrehajtva")
            return True
            
        except Exception as e:
            error_occurred = True
            logger.error(f"Tranzakció hiba: {e}")
            if conn and conn.closed == 0:
                try:
                    conn.rollback()
                except:
                    pass
            raise
            
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                self._put_connection(conn, error=error_occurred)
    
    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Tábla információk lekérése"""
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns 
        WHERE table_name = %s 
        ORDER BY ordinal_position
        """
        
        try:
            result = self.execute_query(query, (table_name,))
            return result
        except Exception as e:
            logger.error(f"Tábla info lekérés hiba {table_name}: {e}")
            return None
    
    def list_tables(self) -> List[str]:
        """Összes tábla listázása"""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        """
        
        try:
            result = self.execute_query(query)
            return [row['table_name'] for row in result]
        except Exception as e:
            logger.error(f"Táblák listázása hiba: {e}")
            return []
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Pool állapot információk debugging-hez"""
        if not self.pool:
            return {"status": "not_initialized"}
        
        try:
            # Privát attribútumok elérése (debugging célból)
            return {
                "status": "active",
                "minconn": getattr(self.pool, '_minconn', 'unknown'),
                "maxconn": getattr(self.pool, '_maxconn', 'unknown'),
                "used_connections": len(getattr(self.pool, '_used', [])),
                "available_connections": len(getattr(self.pool, '_pool', []))
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def close(self):
        """Pool cleanup"""
        try:
            if self.pool:
                self.pool.closeall()
                logger.info("Connection pool lezárva")
        except Exception as e:
            logger.error(f"Pool lezárás hiba: {e}")
        finally:
            self.pool = None