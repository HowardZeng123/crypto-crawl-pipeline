{{ config(
    materialized='view',
    alias='stg_crypto_jobs' -- dbt sẽ tạo ra View tên này trên Supabase
) }}

with raw_data as (
    -- Nhớ đổi tên chỗ này để nó hút data từ bảng thô của mảng Crypto
    select * from {{ source('job_market', 'raw_crypto_jobs') }} 
),

deduplicated as (
    select 
        *,
        row_number() over(
            partition by trim(title), trim(company) 
            order by created_at desc
        ) as rn
    from raw_data
    where title is not null and company is not null
),

cleaned_jobs as (
    select
        id as job_id,
        trim(title) as job_title,
        trim(company) as company_name,
        trim(location) as location,
        trim(salary) as raw_salary,
        
        case 
            when lower(salary) like '%thỏa thuận%' 
              or lower(salary) like '%negotiable%' 
              or lower(salary) like '%cạnh tranh%'
              or lower(salary) like '%thương lượng%'
            then true
            else false
        end as is_salary_hidden,
        
        created_at as ingested_at

    from deduplicated
    where rn = 1 
)

select * from cleaned_jobs
