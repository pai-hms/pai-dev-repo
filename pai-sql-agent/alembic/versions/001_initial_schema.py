"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create population_stats table
    op.create_table('population_stats',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('year', sa.Integer(), nullable=False, comment='기준연도'),
        sa.Column('adm_cd', sa.String(20), nullable=False, comment='행정구역코드'),
        sa.Column('adm_nm', sa.String(255), nullable=True, comment='행정구역명'),
        sa.Column('tot_ppltn', sa.BigInteger(), nullable=True, comment='총인구'),
        sa.Column('avg_age', sa.Float(), nullable=True, comment='평균나이(세)'),
        sa.Column('ppltn_dnsty', sa.Float(), nullable=True, comment='인구밀도(명/㎢)'),
        sa.Column('aged_child_idx', sa.Float(), nullable=True, comment='노령화지수(일백명당 명)'),
        sa.Column('oldage_suprt_per', sa.Float(), nullable=True, comment='노년부양비(일백명당 명)'),
        sa.Column('juv_suprt_per', sa.Float(), nullable=True, comment='유년부양비(일백명당 명)'),
        sa.Column('male_ppltn', sa.BigInteger(), nullable=True, comment='남자인구'),
        sa.Column('female_ppltn', sa.BigInteger(), nullable=True, comment='여자인구'),
        sa.Column('age_0_14', sa.BigInteger(), nullable=True, comment='0-14세 인구'),
        sa.Column('age_15_64', sa.BigInteger(), nullable=True, comment='15-64세 인구'),
        sa.Column('age_65_over', sa.BigInteger(), nullable=True, comment='65세 이상 인구'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_population_year_adm', 'population_stats', ['year', 'adm_cd'])
    op.create_index('idx_population_adm_nm', 'population_stats', ['adm_nm'])

    # Create household_stats table
    op.create_table('household_stats',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('year', sa.Integer(), nullable=False, comment='기준연도'),
        sa.Column('adm_cd', sa.String(20), nullable=False, comment='행정구역코드'),
        sa.Column('adm_nm', sa.String(255), nullable=True, comment='행정구역명'),
        sa.Column('household_cnt', sa.BigInteger(), nullable=True, comment='가구수'),
        sa.Column('avg_household_size', sa.Float(), nullable=True, comment='평균 가구원수'),
        sa.Column('one_person_household', sa.BigInteger(), nullable=True, comment='1인 가구수'),
        sa.Column('elderly_household', sa.BigInteger(), nullable=True, comment='고령자 가구수'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_household_year_adm', 'household_stats', ['year', 'adm_cd'])

    # Create house_stats table
    op.create_table('house_stats',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('year', sa.Integer(), nullable=False, comment='기준연도'),
        sa.Column('adm_cd', sa.String(20), nullable=False, comment='행정구역코드'),
        sa.Column('adm_nm', sa.String(255), nullable=True, comment='행정구역명'),
        sa.Column('house_cnt', sa.BigInteger(), nullable=True, comment='주택수'),
        sa.Column('apartment_cnt', sa.BigInteger(), nullable=True, comment='아파트수'),
        sa.Column('detached_house_cnt', sa.BigInteger(), nullable=True, comment='단독주택수'),
        sa.Column('row_house_cnt', sa.BigInteger(), nullable=True, comment='연립주택수'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_house_year_adm', 'house_stats', ['year', 'adm_cd'])

    # Create company_stats table
    op.create_table('company_stats',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('year', sa.Integer(), nullable=False, comment='기준연도'),
        sa.Column('adm_cd', sa.String(20), nullable=False, comment='행정구역코드'),
        sa.Column('adm_nm', sa.String(255), nullable=True, comment='행정구역명'),
        sa.Column('company_cnt', sa.BigInteger(), nullable=True, comment='사업체수'),
        sa.Column('employee_cnt', sa.BigInteger(), nullable=True, comment='종사자수'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_company_year_adm', 'company_stats', ['year', 'adm_cd'])

    # Create crawl_logs table
    op.create_table('crawl_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('api_endpoint', sa.String(255), nullable=False, comment='API 엔드포인트'),
        sa.Column('year', sa.Integer(), nullable=True, comment='요청 연도'),
        sa.Column('adm_cd', sa.String(20), nullable=True, comment='행정구역코드'),
        sa.Column('status', sa.String(50), nullable=False, comment='크롤링 상태'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='에러 메시지'),
        sa.Column('response_count', sa.Integer(), nullable=True, comment='응답 데이터 개수'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crawl_endpoint_status', 'crawl_logs', ['api_endpoint', 'status'])
    op.create_index('idx_crawl_created_at', 'crawl_logs', ['created_at'])

    # Create langgraph_checkpoints table
    op.create_table('langgraph_checkpoints',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('thread_id', sa.String(255), nullable=False, comment='스레드 ID'),
        sa.Column('checkpoint_id', sa.String(255), nullable=False, comment='체크포인트 ID'),
        sa.Column('parent_checkpoint_id', sa.String(255), nullable=True, comment='부모 체크포인트 ID'),
        sa.Column('checkpoint_data', sa.Text(), nullable=False, comment='체크포인트 데이터 (JSON)'),
        sa.Column('meta_data', sa.Text(), nullable=True, comment='메타데이터 (JSON)'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_checkpoint_thread_id', 'langgraph_checkpoints', ['thread_id'])
    op.create_index('idx_checkpoint_checkpoint_id', 'langgraph_checkpoints', ['checkpoint_id'])
    op.create_index('idx_checkpoint_parent_id', 'langgraph_checkpoints', ['parent_checkpoint_id'])
    op.create_index('idx_checkpoint_created_at', 'langgraph_checkpoints', ['created_at'])


def downgrade() -> None:
    op.drop_table('langgraph_checkpoints')
    op.drop_table('crawl_logs')
    op.drop_table('company_stats')
    op.drop_table('house_stats')
    op.drop_table('household_stats')
    op.drop_table('population_stats')
