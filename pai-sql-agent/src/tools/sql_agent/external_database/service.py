"""
ExternalDatabaseService - SQLAlchemy 연결/관리 서비스
SQL Agent에서 외부 데이터베이스 연결 및 관리 담당
"""
import asyncio
import logging
from contextlib import AbstractContextManager, asynccontextmanager
from typing import Callable, Dict, List

import sqlalchemy.exc
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker, async_scoped_session
from sqlalchemy.pool import NullPool
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field

from src.database.base import Base
from src.exceptions import DatabaseException, NotFoundException, DBIntegrityException
from .database import CustomSQLDatabase

logger = logging.getLogger(__name__)


class QueryItem(BaseModel):
    """쿼리 아이템 나타내는 모델"""
    query: str = Field(description="생성된 쿼리 문자열")
    description: str = Field(description="해당 쿼리의 설명 문자열")


class GeneratedQueries(BaseModel):
    """생성된 쿼리 목록을 나타내는 모델"""
    queries: List[QueryItem] = Field(description="생성된 쿼리 목록")


async def generate_queries(llm: BaseLanguageModel, text: str) -> List[Dict[str, str]]:
    """
    주어진 텍스트로부터 SQL 쿼리를 생성
    
    Args:
        llm: 쿼리 생성을 위한 언어 모델
        text: 쿼리를 생성할 기준이 되는 텍스트
        
    Returns:
        List[Dict[str, str]]: 생성된 쿼리 목록 (쿼리 문자열과 설명 포함)
    """
    from src.agent.prompt import get_query_generation_service_prompt
    
    parser = JsonOutputParser(pydantic_schema=GeneratedQueries)
    
    # 프롬프트 템플릿 생성
    base_prompt = get_query_generation_service_prompt(text)
    prompt_with_format = base_prompt.replace(
        "{text}", 
        f"{text}\n\n다음 JSON 형식으로 응답해주세요:\n{{format_instructions}}"
    )
    
    prompt_template = ChatPromptTemplate.from_template(prompt_with_format)
    
    chain = prompt_template.pipe(llm).pipe(parser)
    
    result = await chain.ainvoke(
        {
            "text": text,
            "format_instructions": parser.get_format_instructions(),
        }
    )
    
    return result.get("queries", [])


class ExternalDatabaseService:
    """외부 데이터베이스 연결 및 관리를 담당하는 클래스"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.db = None
        self._engine = None
        self._session_factory = None
        logger.info("ExternalDatabaseService 초기화됨")

    def init_db(self, database_url: str) -> CustomSQLDatabase:
        """
        데이터베이스 초기화 - CustomSQLDatabase 인스턴스 생성
        
        Args:
            database_url: 연결할 데이터베이스 URL
            
        Returns:
            CustomSQLDatabase: 초기화된 데이터베이스 인스턴스
        """
        logger.info(f"외부 데이터베이스 URL로 초기화: {database_url}")
        self.db = CustomSQLDatabase.from_uri(database_url)
        
        # SQLAlchemy 엔진도 함께 생성 (세션 관리용)
        self._engine = create_async_engine(
            database_url, 
            poolclass=NullPool, 
            echo=False
        )
        
        self._session_factory = async_scoped_session(
            async_sessionmaker(
                autocommit=False,
                bind=self._engine,
            ),
            scopefunc=asyncio.current_task,
        )
        
        return self.db

    async def create_database(self) -> None:
        """데이터베이스 테이블 생성"""
        if not self._engine:
            raise DatabaseException("데이터베이스가 초기화되지 않았습니다")
            
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_database(self) -> None:
        """데이터베이스 테이블 삭제"""
        if not self._engine:
            raise DatabaseException("데이터베이스가 초기화되지 않았습니다")
            
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @asynccontextmanager
    async def get_session(self) -> Callable[..., AbstractContextManager[AsyncSession]]:
        """
        비동기 세션 컨텍스트 매니저
        
        Returns:
            AsyncSession: SQLAlchemy 비동기 세션
        """
        if not self._session_factory:
            raise DatabaseException("세션 팩토리가 초기화되지 않았습니다")
            
        session: AsyncSession = self._session_factory()
        try:
            yield session
        except sqlalchemy.exc.NoResultFound:
            await session.rollback()
            raise NotFoundException("데이터를 찾을 수 없습니다")
        except sqlalchemy.exc.IntegrityError:
            await session.rollback()
            raise DBIntegrityException("데이터 무결성 제약 조건 위반")
        except Exception as e:
            logger.exception("Session rollback because of exception")
            await session.rollback()
            raise e
        finally:
            await session.close()
            await self._session_factory.remove()

    async def connect(self):
        """
        데이터베이스 연결
        
        Returns:
            connection: 데이터베이스 연결 객체
        """
        if not self._engine:
            raise DatabaseException("데이터베이스 엔진이 초기화되지 않았습니다")
            
        return await self._engine.connect()

    async def ping_database(self, database_url: str) -> bool:
        """
        데이터베이스 URL의 연결 상태를 확인하는 ping 테스트
        
        Args:
            database_url: 테스트할 데이터베이스 URL
            
        Returns:
            bool: 연결 가능 여부 (True: 연결 성공, False: 연결 실패)
        """
        try:
            # 임시로 데이터베이스 연결 생성
            temp_db = CustomSQLDatabase.from_uri(database_url)
            
            # 간단한 쿼리 실행으로 연결 테스트
            temp_db._retrieve_content_from_db("SELECT 1")
            
            return True
        except Exception as e:
            # 연결 실패 시 로그 남기고 False 반환
            logger.error(f"데이터베이스 연결 테스트 실패: {str(e)}")
            return False
