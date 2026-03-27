"""
Gerenciador de PostgreSQL para Armazenamento e Análise de Dados Econômicos
"""
import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, Column, Float, String, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import sqlalchemy as sa

from config import SQLALCHEMY_DATABASE_URL, DATABASE_CACHE_MINUTES

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()


class EconomicIndicator(Base):
    """Modelo de dados para indicadores econômicos"""
    __tablename__ = "economic_indicators"
    
    id = sa.Column(sa.Integer, primary_key=True)
    date = sa.Column(sa.DateTime, nullable=False, index=True)
    country_code = sa.Column(sa.String(3), index=True)
    country_name = sa.Column(sa.String(100))
    indicator_code = sa.Column(sa.String(50), index=True)
    indicator_name = sa.Column(sa.String(200))
    value = sa.Column(sa.Float)
    api_source = sa.Column(sa.String(50))
    timestamp_created = sa.Column(sa.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_date_country_indicator', 'date', 'country_code', 'indicator_code'),
    )


class PostgreSQLManager:
    """Gerenciador profissional de PostgreSQL para dados econômicos"""
    
    def __init__(self):
        """Inicializa conexão com PostgreSQL"""
        try:
            self.engine = create_engine(
                SQLALCHEMY_DATABASE_URL,
                echo=False,
                pool_size=10,
                max_overflow=20
            )
            
            # Criar todas as tabelas
            Base.metadata.create_all(self.engine)
            self.SessionLocal = sessionmaker(bind=self.engine)
            
            logger.info("✓ PostgreSQL inicializado com sucesso")
        
        except Exception as e:
            logger.error(f"❌ Erro ao conectar em PostgreSQL: {str(e)}")
            raise
    
    def insert_data(self, df: pd.DataFrame, 
                   country_code: str, 
                   indicator_code: str,
                   indicator_name: str,
                   api_source: str) -> int:
        """
        Insere dados econômicos no PostgreSQL
        
        Args:
            df: DataFrame com colunas ['date', 'value']
            country_code: Código do país (ex: 'BR')
            indicator_code: Código único do indicador
            indicator_name: Nome do indicador
            api_source: Fonte da API
            
        Returns:
            Número de linhas inseridas
        """
        if df.empty:
            logger.warning(f"DataFrame vazio para {indicator_code}")
            return 0
        
        try:
            session = self.SessionLocal()
            inserted = 0
            
            for _, row in df.iterrows():
                # Verificar se já existe
                existing = session.query(EconomicIndicator).filter(
                    EconomicIndicator.date == row['date'],
                    EconomicIndicator.country_code == country_code,
                    EconomicIndicator.indicator_code == indicator_code
                ).first()
                
                if not existing:
                    indicator = EconomicIndicator(
                        date=pd.to_datetime(row['date']),
                        country_code=country_code,
                        country_name=row.get('country_name', ''),
                        indicator_code=indicator_code,
                        indicator_name=indicator_name,
                        value=float(row['value']) if pd.notna(row['value']) else None,
                        api_source=api_source
                    )
                    session.add(indicator)
                    inserted += 1
            
            session.commit()
            session.close()
            logger.info(f"✓ {inserted} registros inseridos para {indicator_code}")
            return inserted
        
        except Exception as e:
            logger.error(f"Erro ao inserir dados: {str(e)}")
            session.rollback()
            session.close()
            return 0
    
    def get_indicator_data(self, 
                          indicator_code: str,
                          country_code: Optional[str] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """
        Obtém dados de um indicador do PostgreSQL
        
        Args:
            indicator_code: Código do indicador
            country_code: Código do país (opcional)
            start_date: Data inicial (YYYY-MM-DD)
            end_date: Data final (YYYY-MM-DD)
            
        Returns:
            DataFrame com dados
        """
        try:
            session = self.SessionLocal()
            query = session.query(EconomicIndicator).filter(
                EconomicIndicator.indicator_code == indicator_code
            )
            
            if country_code:
                query = query.filter(EconomicIndicator.country_code == country_code)
            
            if start_date:
                query = query.filter(EconomicIndicator.date >= pd.to_datetime(start_date))
            
            if end_date:
                query = query.filter(EconomicIndicator.date <= pd.to_datetime(end_date))
            
            results = query.order_by(EconomicIndicator.date).all()
            session.close()
            
            # Converter para DataFrame
            if not results:
                return pd.DataFrame()
            
            data = [{
                'date': r.date,
                'country_code': r.country_code,
                'country_name': r.country_name,
                'value': r.value,
                'api_source': r.api_source
            } for r in results]
            
            return pd.DataFrame(data)
        
        except Exception as e:
            logger.error(f"Erro ao obter dados: {str(e)}")
            return pd.DataFrame()
    
    def get_multiple_indicators(self, 
                               indicator_codes: List[str],
                               country_code: str,
                               start_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Obtém múltiplos indicadores para análise
        
        Args:
            indicator_codes: Lista de códigos de indicadores
            country_code: Código do país
            start_date: Data inicial
            
        Returns:
            Dicionário com DataFrames para cada indicador
        """
        results = {}
        
        for code in indicator_codes:
            df = self.get_indicator_data(code, country_code, start_date)
            results[code] = df
        
        return results
    
    def get_correlation_data(self, 
                            country_code: str,
                            start_date: Optional[str] = None) -> pd.DataFrame:
        """
        Obtém todos os dados para análise de correlação
        
        Args:
            country_code: Código do país
            start_date: Data inicial
            
        Returns:
            DataFrame pivotado com indicadores como colunas
        """
        try:
            session = self.SessionLocal()
            query = session.query(EconomicIndicator).filter(
                EconomicIndicator.country_code == country_code
            )
            
            if start_date:
                query = query.filter(EconomicIndicator.date >= pd.to_datetime(start_date))
            
            results = query.all()
            session.close()
            
            if not results:
                return pd.DataFrame()
            
            data = [{
                'date': r.date,
                'indicator_code': r.indicator_code,
                'value': r.value
            } for r in results]
            
            df = pd.DataFrame(data)
            
            # Pivotar para ter indicadores como colunas
            df_pivot = df.pivot_table(
                index='date',
                columns='indicator_code',
                values='value',
                aggfunc='first'
            )
            
            return df_pivot.sort_index()
        
        except Exception as e:
            logger.error(f"Erro ao obter dados de correlação: {str(e)}")
            return pd.DataFrame()
    
    def delete_old_data(self, days: int = 365 * 10) -> int:
        """
        Remove dados mais antigos que N dias (limpeza)
        
        Args:
            days: Número de dias a manter
            
        Returns:
            Número de registros deletados
        """
        try:
            session = self.SessionLocal()
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted = session.query(EconomicIndicator).filter(
                EconomicIndicator.date < cutoff_date
            ).delete()
            
            session.commit()
            session.close()
            logger.info(f"✓ {deleted} registros antigos deletados")
            return deleted
        
        except Exception as e:
            logger.error(f"Erro ao deletar dados antigos: {str(e)}")
            return 0
    
    def get_statistics(self, 
                      indicator_code: str,
                      country_code: str) -> Dict:
        """
        Obtém estatísticas descritivas de um indicador
        
        Args:
            indicator_code: Código do indicador
            country_code: Código do país
            
        Returns:
            Dicionário com estatísticas
        """
        df = self.get_indicator_data(indicator_code, country_code)
        
        if df.empty or 'value' not in df.columns:
            return {}
        
        values = df['value'].dropna()
        
        return {
            'count': len(values),
            'mean': float(values.mean()),
            'std': float(values.std()),
            'min': float(values.min()),
            'max': float(values.max()),
            'median': float(values.median()),
            'latest_date': str(df['date'].max()),
            'latest_value': float(df['value'].iloc[-1]) if not df.empty else None
        }
    
    def raw_sql_query(self, sql: str) -> pd.DataFrame:
        """
        Executa query SQL customizada
        
        Args:
            sql: Query SQL
            
        Returns:
            DataFrame com resultados
        """
        try:
            return pd.read_sql_query(sql, self.engine)
        except Exception as e:
            logger.error(f"Erro ao executar SQL: {str(e)}")
            return pd.DataFrame()
    
    def get_database_info(self) -> Dict:
        """Retorna informações sobre o banco de dados"""
        try:
            session = self.SessionLocal()
            
            total_records = session.query(EconomicIndicator).count()
            unique_indicators = session.query(
                EconomicIndicator.indicator_code
            ).distinct().count()
            unique_countries = session.query(
                EconomicIndicator.country_code
            ).distinct().count()
            
            session.close()
            
            return {
                'total_records': total_records,
                'unique_indicators': unique_indicators,
                'unique_countries': unique_countries,
                'database_url': SQLALCHEMY_DATABASE_URL.replace(
                    SQLALCHEMY_DATABASE_URL.split('@')[0],
                    'postgresql://***'
                )
            }
        
        except Exception as e:
            logger.error(f"Erro ao obter info do banco: {str(e)}")
            return {}
