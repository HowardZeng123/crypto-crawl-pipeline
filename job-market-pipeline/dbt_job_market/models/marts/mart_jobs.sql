{{ config(
    materialized='incremental',
    unique_key='job_id',
    on_schema_change='sync_all_columns',
    alias='mart_crypto_jobs' -- dbt sẽ tạo ra bảng tên này trên Supabase
) }}

with staging as (
    -- Lấy data từ lớp Silver (dùng ref thay vì source)
    select * from {{ ref('stg_jobs') }}
    {% if is_incremental() %}
    where ingested_at > (select coalesce(max(ingested_at), '1900-01-01') from {{ this }})
    {% endif %}
),

extracted_numbers as (
    select
        job_id,
        job_title,
        company_name,
        location,
        raw_salary,
        is_salary_hidden,
        
        -- Dùng Regex bóc tách con số đầu tiên xuất hiện trong chuỗi
        -- Ví dụ: "15 - 20 triệu" -> 15. "Upto $1000" -> 1000
        substring(raw_salary from '([0-9]+)')::numeric as min_salary_val,
        
        -- Nhận diện đơn vị tiền tệ để quy đổi
        case 
            when lower(raw_salary) like '%usd%' or raw_salary like '%$%' then 'USD'
            when lower(raw_salary) like '%triệu%' or lower(raw_salary) like '%tr%' then 'VND_MILLION'
            else 'UNKNOWN'
        end as currency_type,

        ingested_at
    from staging
),

final_mart as (
    select 
        *,
        -- Quy đổi sương sương tất cả ra Triệu VNĐ (Tỷ giá giả định 1 USD = 25,000 VND)
        case 
            when currency_type = 'USD' then min_salary_val * 25 / 1000
            when currency_type = 'VND_MILLION' then min_salary_val
            else null
        end as estimated_salary_vnd_million
    from extracted_numbers
)

select * from final_mart
