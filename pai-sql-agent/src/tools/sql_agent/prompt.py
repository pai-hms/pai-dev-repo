"""
 DEPRECATED: ì íì¼ì ë ìì ì‚ì©ë˜ì ììë‹ë‹.
ìëì ìì™ììì‹ íëíí ì‹ìíì ì‚ì©í˜ìì: src/agent/prompt.py

ëë íëííë src/agent/prompt.pyìì êë¦ë©ë‹ë‹.
"""

# íìë ìí‚ë ì°í ì¿¼ë¦
TABLE_SCHEMA_QUERY = """SELECT 
    a.attname as column_name,
    format_type(a.atttypid, a.atttypmod) as data_type,
    CASE 
        WHEN p.contype = 'p' THEN true
        ELSE false
    END as primary_key,
    not (a.attnotnull) as nullable,
    pg_catalog.col_description(a.attrelid, a.attnum) as description
FROM pg_catalog.pg_attribute a
LEFT JOIN pg_catalog.pg_constraint p 
    ON p.conrelid = a.attrelid 
    AND a.attnum = ANY(p.conkey)
    AND p.contype = 'p'
WHERE a.attrelid = '{table_name}'::regclass
    AND a.attnum > 0 
    AND NOT a.attisdropped
ORDER BY a.attnum;"""

# ì˜í ë°ìí° ì°í ì¿¼ë¦
SAMPLE_ROWS_QUERY = """
SELECT * 
FROM {table_name}
LIMIT {sample_rows}
"""

# íìë ìë³ íë
TABLE_INFO_FORMAT = """
table name: `{table_name}`

/*
table schema
{table_schema}*/

/*
{num_sample_rows} rows from `{table_name}`:
{sample_rows}*/
"""

# SQL ìì ìì© íëíí
QUERY_GENERATION_PROMPT = """You are a SQL expert with a strong attention to detail.

Given an input question, output a syntactically correct {dialect} query to run.

**ABSOLUTE REQUIREMENT**: You MUST use the sql_db_query tool for ALL database operations.

**CRITICAL - TOOL NAME**: The exact name of the tool is 'sql_db_query' - NOT 'sql_query' or any variation.

When generating the query:

1. **Select Strategy**:
   - Select only the necessary columns to answer the question
   - If the table contains time-related fields (`year`, `month`, `date`, `timestamp`), include them when relevant
   - Include categorical identifiers or grouping keys if they help distinguish different data groups
   - Avoid selecting unnecessary columns to minimize token usage

2. **Result Limiting**:
   - Limit the query to at most 200 results unless the user specifies otherwise
   - Order the results by a relevant column (e.g., chronological order for time-series data, descending order for rankings)
   - If multiple time-related columns exist, prefer the most granular one (`timestamp` > `date` > `year, month`)

3. **Error Handling**:
   - If the initial query results in an error, rewrite and retry the query
   - If the query returns an empty result set, adjust filters or ordering to retrieve a meaningful dataset

4. **Security Rules**:
   - Do NOT generate DML statements (INSERT, UPDATE, DELETE, DROP, etc.)
   - Only SELECT queries are allowed

5. **Fallback Strategy**:
   - If there isn't enough information to generate a query, simply state that the available data is insufficient

## Database Information

{table_infos}

## Instructions
- Analyze the user's question carefully
- Identify the relevant tables and columns
- Generate an efficient and accurate SQL query
- Use the sql_db_query tool to execute the query
- If errors occur, debug and retry with improved query"""
