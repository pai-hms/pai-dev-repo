"""
CustomSQLDatabase - LangChain SQLDatabase 확장
SQL Agent에서 사용할 커스텀 DB 유틸리티 클래스
"""
import io
import pandas as pd
from typing import Any, Dict, List, Literal, Optional, Union
from decimal import Decimal
from sqlalchemy import Executable
from langchain_community.utilities import SQLDatabase

from ..prompt import TABLE_SCHEMA_QUERY, SAMPLE_ROWS_QUERY, TABLE_INFO_FORMAT


class CustomSQLDatabase(SQLDatabase):
    """
    LangChain SQLDatabase를 확장한 커스텀 데이터베이스 클래스
    CSV 형태 결과 반환 및 향상된 테이블 정보 제공
    """

    def run_with_headers(
        self,
        command: Union[str, Executable],
        fetch: Literal["all", "one", "cursor"] = "all",
        *,
        parameters: Optional[Dict[str, Any]] = None,
        execution_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        SQL 쿼리 실행하고 헤더를 포함한 CSV 형태의 결과를 반환

        Args:
            command: 실행할 SQL 명령
            fetch: 결과 가져오기 방식
            parameters: 쿼리 파라미터
            execution_options: 실행 옵션

        Returns:
            str: CSV 형태 결과 문자열
        """

        # 부모 클래스의 _execute 메서드 사용하여 쿼리 실행
        result = self._execute(
            command, fetch, parameters=parameters, execution_options=execution_options
        )

        if fetch == "cursor":
            return result

        # 결과를 DataFrame으로 변환
        df = pd.DataFrame([
            {
                column: self._truncate_word(value, length=self._max_string_length)
                for column, value in r.items()
            }
            for r in result
        ])
        
        # CSV 형태 변환하여 반환
        return df.to_csv(index=False)

    def get_table_info(self, table_names: Optional[List[str]] = None) -> str:
        """
        테이블 정보를 상세히 조회
        
        포함 내용:
        - 테이블 스키마 정보
        - 샘플 데이터 미리보기
        - 컬럼별 설명

        Args:
            table_names: 조회할 테이블 이름 목록 (선택)

        Returns:
            str: 포맷된 테이블 정보
        """
        all_table_names = self.get_usable_table_names()

        if table_names is not None:
            # 요청된 테이블이 실제로 존재하는지 확인
            if missing_tables := set(table_names).difference(all_table_names):
                raise ValueError(f"table_names {missing_tables} not found in database")
            all_table_names = table_names

        tables = []
        for table_name in all_table_names:
            try:
                # 테이블 스키마 정보 조회
                table_schema = self._retrieve_content_from_db(
                    TABLE_SCHEMA_QUERY.format(table_name=table_name)
                )
                
                # 샘플 데이터 조회
                sample_rows = self._retrieve_content_from_db(
                    SAMPLE_ROWS_QUERY.format(
                        table_name=table_name, 
                        sample_rows=self._sample_rows_in_table_info
                    )
                )
                
                # 테이블 정보 포맷팅
                table_info = TABLE_INFO_FORMAT.format(
                    table_name=table_name,
                    num_sample_rows=self._sample_rows_in_table_info,
                    table_schema=table_schema,
                    sample_rows=sample_rows,
                )
                tables.append(table_info)
                
            except Exception as e:
                # 개별 테이블 조회 실패 시에도 전체 작업은 계속
                tables.append(f"table name: `{table_name}` (조회 실패: {str(e)})")

        return "\n\n".join(tables)

    def _retrieve_content_from_db(self, query: str) -> str:
        """
        데이터베이스에서 쿼리 결과를 가져와서 문자열로 반환
        
        Args:
            query: 실행할 쿼리
            
        Returns:
            str: 탭으로 구분된 결과
        """
        try:
            # 쿼리 실행 및 결과 가져오기
            raw_content = self.run(query, include_columns=True)
            
            # CSV 문자열을 DataFrame으로 변환
            df = pd.read_csv(io.StringIO(raw_content))
            
            # 탭 구분 형태로 변환
            return df.to_csv(sep="\t", index=False)
            
        except Exception as e:
            # 변환 실패시 빈 DataFrame 반환
            return pd.DataFrame().to_csv(sep="\t", index=False)

    def _truncate_word(self, content: Any, *, length: int, suffix: str = "...") -> str:
        """
        문자열을 지정된 길이로 자르기
        
        Args:
            content: 자를 내용
            length: 최대 길이
            suffix: 잘린 부분을 나타내는 접미사
            
        Returns:
            str: 잘린 문자열
        """
        if not isinstance(content, str) or length <= 0:
            return str(content)

        if len(content) <= length:
            return content

        return content[: length - len(suffix)].rsplit(" ", 1)[0] + suffix


def create_sql_database(database_url: str) -> CustomSQLDatabase:
    """
    데이터베이스 URL로부터 CustomSQLDatabase 인스턴스 생성
    
    Args:
        database_url: 데이터베이스 연결 URL
        
    Returns:
        CustomSQLDatabase: 생성된 SQL 데이터베이스 인스턴스
    """
    # checkpoint_* 테이블은 langchain에서 자동으로 생성되므로 제외
    return CustomSQLDatabase.from_uri(database_url)
