import os
import requests
import psycopg
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Lấy biến môi trường
DB_CONN = os.getenv('DB_CONN')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

def send_discord_alert(job):
    """Đóng gói data thành một cái thẻ (Embed) siêu đẹp trên Discord"""
    
    # job = (job_id, job_title, company_name, location, raw_salary, estimated_salary)
    title = job[1]
    company = job[2]
    location = job[3]
    raw_salary = job[4]
    est_salary = job[5]
    
    # Format lại hiển thị lương
    if est_salary:
        salary_display = f"**{raw_salary}** (Khoảng {est_salary} triệu VNĐ)"
    else:
        salary_display = f"**{raw_salary}**"

    payload = {
        "username": "Crypto Job Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/4712/4712139.png", # Icon cho xịn
        "embeds": [{
            "title": f"🚀 JOBS MỚI: {title}",
            "color": 5814783, # Màu xanh lá/xanh dương
            "fields": [
                {"name": "🏢 Công ty", "value": company, "inline": False},
                {"name": "💰 Mức lương", "value": salary_display, "inline": False},
                {"name": "📍 Địa điểm", "value": location, "inline": False}
            ],
            "footer": {"text": "Dữ liệu được làm sạch bởi dbt 🪄"}
        }]
    }
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Lỗi gửi Discord: {e}")
        return False

def main():
    if not DISCORD_WEBHOOK_URL:
        print("Chưa có DISCORD_WEBHOOK_URL trong file .env!")
        return

    print("Đang quét các job mới từ mart_jobs...")
    try:
        conn = psycopg.connect(DB_CONN)
        cur = conn.cursor()
        
        # TUYỆT CHIÊU: Trích xuất các job nằm trong mart_jobs nhưng CHƯA CÓ trong alert_history
        cur.execute("""
            SELECT job_id, job_title, company_name, location, raw_salary, estimated_salary_vnd_million 
            FROM mart_jobs 
            WHERE job_id NOT IN (SELECT job_id FROM alert_history)
        """)
        
        new_jobs = cur.fetchall()
        
        if not new_jobs:
            print("Chưa có job nào mới. Sếp cứ yên tâm đi ngủ!")
            return

        alert_count = 0
        for job in new_jobs:
            job_id = job[0]
            
            # Nếu gửi Discord thành công thì mới lưu vào lịch sử
            if send_discord_alert(job):
                cur.execute("INSERT INTO alert_history (job_id) VALUES (%s)", (job_id,))
                conn.commit()
                alert_count += 1
                
        print(f"✅ Đã bắn {alert_count} jobs mới vào Discord!")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Lỗi database: {e}")

if __name__ == "__main__":
    main()