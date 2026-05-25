# Job Market Pipeline

End-to-end data pipeline that crawls job postings from multiple sources, loads raw data into Postgres/Supabase, transforms it with dbt, and sends new-job alerts to Discord.

## Architecture

Sources -> Crawlers (Python) -> raw_jobs (Postgres/Supabase)
    -> dbt staging (dedup + clean) -> dbt mart (salary parsing)
    -> Discord alert bot

<img width="2360" height="660" alt="Untitled-2026-04-25-2046" src="https://github.com/user-attachments/assets/cd20fcfc-1ed7-419a-8aad-6fe7f79bef13" />

## Tech Stack

- Python (requests, psycopg, dotenv)
- Postgres/Supabase (raw storage)
- dbt (staging + mart models)
- GitHub Actions (scheduled orchestration)
- Discord Webhook (alerts)

## Project Structure

- crawler/: source-specific crawlers
- dbt_job_market/: dbt project (staging + marts)
- alert_bot.py: sends alerts for new jobs
- .github/workflows/pipeline.yml: daily scheduled pipeline

## Data Models

- raw_jobs: raw ingestion table
- stg_jobs: deduplicated and cleaned jobs
- mart_jobs: salary parsing and analytics-ready output

## Orchestration (GitHub Actions)

- Schedule: daily at 00:00 UTC
- Steps: run crawlers -> dbt run -> send Discord alerts
- Workflow: .github/workflows/pipeline.yml

## Setup (Local)

1) Create a .env file with:
   - DB_CONN
   - DISCORD_WEBHOOK_URL
   - ITVIEC_COOKIE
2) Install dependencies:

```bash
pip install -r requirements.txt
pip install dbt-postgres
```

3) Run crawlers:

```bash
python crawler/itviec_crawler.py
python crawler/vnworks_crawler.py
python crawler/topcv_crawler.py
python crawler/joboko_crawler.py
python crawler/linkedin_crawler.py
```

4) Run dbt:

```bash
dbt run --project-dir dbt_job_market --profiles-dir dbt_job_market --target dev
```

5) Send alerts:

```bash
python alert_bot.py
```

## Notes

- Dedup happens in dbt staging (stg_jobs)
- Salary normalization happens in mart_jobs
