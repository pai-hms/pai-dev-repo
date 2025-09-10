-- pgvector 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;

-- 문서 임베딩 테이블 생성
CREATE TABLE IF NOT EXISTS document_embeddings (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    source_table VARCHAR(100),
    source_id VARCHAR(50),
    meta_data JSONB DEFAULT '{}',
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small 차원
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 벡터 유사도 검색용 인덱스 (IVFFlat)
CREATE INDEX IF NOT EXISTS document_embeddings_embedding_cosine_idx 
ON document_embeddings USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 메타데이터 검색용 인덱스
CREATE INDEX IF NOT EXISTS document_embeddings_source_idx 
ON document_embeddings (source_table, source_id);

CREATE INDEX IF NOT EXISTS document_embeddings_metadata_idx 
ON document_embeddings USING gin (meta_data);

-- 업데이트 시간 자동 갱신 함수
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 업데이트 트리거 생성
DROP TRIGGER IF EXISTS update_document_embeddings_modtime ON document_embeddings;
CREATE TRIGGER update_document_embeddings_modtime 
    BEFORE UPDATE ON document_embeddings 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- 통계 데이터 요약 뷰 생성 (임베딩 생성용)
CREATE OR REPLACE VIEW stats_summary_for_embedding AS
SELECT 
    CONCAT('stats_', adm_cd, '_', year) as id,
    adm_cd,
    adm_nm,
    year,
    'population_stats' as source_table,
    CONCAT(
        adm_nm, ' ', year, '년 통계: ',
        '총인구 ', COALESCE(tot_ppltn::text, '정보없음'), '명, ',
        '평균연령 ', COALESCE(avg_age::text, '정보없음'), '세, ',
        '인구밀도 ', COALESCE(ppltn_dnsty::text, '정보없음'), '명/㎢, ',
        '노령화지수 ', COALESCE(aged_child_idx::text, '정보없음'), ', ',
        '남성 ', COALESCE(male_ppltn::text, '정보없음'), '명, ',
        '여성 ', COALESCE(female_ppltn::text, '정보없음'), '명'
    ) as description,
    json_build_object(
        'year', year,
        'total_population', tot_ppltn,
        'avg_age', avg_age,
        'population_density', ppltn_dnsty,
        'aging_index', aged_child_idx,
        'male_population', male_ppltn,
        'female_population', female_ppltn
    ) as meta_data
FROM population_stats
WHERE year >= 2020  -- 최근 데이터만
AND tot_ppltn IS NOT NULL;

-- 함수: 통계 데이터 임베딩 배치 삽입용 헬퍼
CREATE OR REPLACE FUNCTION upsert_stats_embedding(
    p_id TEXT,
    p_content TEXT,
    p_source_table TEXT,
    p_source_id TEXT,
    p_meta_data JSONB,
    p_embedding VECTOR(1536)
) RETURNS VOID AS $$
BEGIN
    INSERT INTO document_embeddings (content, source_table, source_id, meta_data, embedding)
    VALUES (p_content, p_source_table, p_source_id, p_meta_data, p_embedding)
    ON CONFLICT (source_table, source_id) 
    DO UPDATE SET 
        content = EXCLUDED.content,
        meta_data = EXCLUDED.meta_data,
        embedding = EXCLUDED.embedding,
        updated_at = CURRENT_TIMESTAMP;
END;
$$ LANGUAGE plpgsql;

-- 인덱스 최적화를 위한 제약조건 추가
ALTER TABLE document_embeddings 
ADD CONSTRAINT unique_source_record UNIQUE (source_table, source_id);

COMMENT ON TABLE document_embeddings IS 'AI 임베딩 저장 테이블 - pgvector 기반 의미 검색';
COMMENT ON COLUMN document_embeddings.embedding IS 'OpenAI text-embedding-3-small 1536차원 벡터';
COMMENT ON INDEX document_embeddings_embedding_cosine_idx IS 'IVFFlat 인덱스 - 코사인 유사도 기반 벡터 검색';
