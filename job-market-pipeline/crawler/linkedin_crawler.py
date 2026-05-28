import os
from curl_cffi import requests
from bs4 import BeautifulSoup
import psycopg
from dotenv import load_dotenv, find_dotenv
from datetime import datetime
import time
from urllib.parse import quote_plus

load_dotenv(find_dotenv())

KEYWORDS = [
    "crypto exchange",
    "crypto risk",
    "trading operations",
]

# THÊM DANH SÁCH ĐỊA ĐIỂM VÀO ĐÂY BRO NHÉ
LOCATIONS = [
    "Taiwan",
    "Asia Pacific" # Dùng chữ này thay cho APAC để LinkedIn dễ hiểu
]

def get_db_connection():
    db_url = os.getenv('DB_CONN')
    if not db_url:
        print("Lỗi: Không tìm thấy biến DB_CONN.")
        return None
    try:
        return psycopg.connect(db_url)
    except Exception as e:
        print(f"Lỗi kết nối Database: {e}")
        return None


def ensure_raw_crypto_jobs_table(conn):
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                create table if not exists raw_crypto_jobs (
                    id bigserial primary key,
                    title text,
                    company text,
                    salary text,
                    location text,
                    created_at timestamptz default now()
                )
                """
            )
        conn.commit()
    except Exception as e:
        print(f"Lỗi khi tạo bảng raw_crypto_jobs: {e}")
        conn.rollback()

def crawl_linkedin():
    print("Bắt đầu cào dữ liệu từ LinkedIn (Guest API)...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    job_list = []
    seen_jobs = set()
    
    # 1. Lặp qua từng địa điểm
    for loc in LOCATIONS:
        location_param = quote_plus(loc)
        
        # 2. Lặp qua từng từ khóa
        for keyword in KEYWORDS:
            keyword_param = quote_plus(keyword)
            
            # Cào thử 2 trang
            for page_num in range(2):
                start_index = page_num * 25
                print(f"Đang cào LinkedIn ({keyword} tại {loc}) từ vị trí {start_index}...")
                
                # Truyền biến location_param vào URL
                url = (
                    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
                    f"?keywords={keyword_param}&location={location_param}&start={start_index}"
                )
                
                # Nếu muốn cào CHUYÊN REMOTE, bro có thể dùng dòng url dưới này thay thế:
                # url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={keyword_param}&location={location_param}&f_WT=2&start={start_index}"
                
                try:
                    response = requests.get(url, impersonate="chrome120", headers=headers)
                    
                    if response.status_code != 200:
                        print(f"Bị Microsoft chặn rồi! Mã lỗi: {response.status_code}")
                        break
                        
                    soup = BeautifulSoup(response.text, 'html.parser')
                    jobs = soup.find_all('li')
                    
                    if not jobs:
                        print("Không còn job nào hoặc bị block IP tạm thời.")
                        break

                    for job in jobs:
                        try:
                            title_elem = job.find('h3', class_='base-search-card__title')
                            title = title_elem.text.strip() if title_elem else "N/A"
                            
                            if title == "N/A":
                                continue 
                                
                            company_elem = job.find('h4', class_='base-search-card__subtitle')
                            company = company_elem.text.strip() if company_elem else "N/A"
                            
                            location_elem = job.find('span', class_='job-search-card__location')
                            # Đổi default fallback thành chính cái 'loc' đang search
                            location = location_elem.text.strip() if location_elem else loc
                            
                            salary_elem = job.find('span', class_='job-search-card__salary-info')
                            salary = salary_elem.text.strip() if salary_elem else "Thỏa thuận"

                            job_key = (title, company, location)
                            if job_key in seen_jobs:
                                continue
                            seen_jobs.add(job_key)
                            job_list.append((title, company, salary, location))
                        except Exception as e:
                            continue
                    
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"Lỗi khi request LinkedIn: {e}")
                    break
            
    print(f"Đã hút được {len(job_list)} jobs từ LinkedIn.")
    return job_list

def insert_to_supabase(conn, jobs_data):
    if not jobs_data: return
    print("Đang đẩy dữ liệu lên Supabase...")
    try:
        with conn.cursor() as cur:
            for job in jobs_data:
                # Dùng ON CONFLICT DO NOTHING để chống trùng lặp y chang cái cũ
                cur.execute(
                    """
                    INSERT INTO raw_crypto_jobs (title, company, salary, location, created_at) 
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (job[0], job[1], job[2], job[3], datetime.now())
                )
            conn.commit()
            print("Đã đẩy thành công lên Database!")
    except Exception as e:
        print(f"Lỗi khi insert: {e}")
        conn.rollback()

def main():
    conn = get_db_connection()
    if conn:
        ensure_raw_crypto_jobs_table(conn)
        jobs_data = crawl_linkedin()
        insert_to_supabase(conn, jobs_data)
        conn.close()

if __name__ == "__main__":
    main()