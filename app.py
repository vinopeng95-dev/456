from flask import Flask, request, render_template_string
import requests
from bs4 import BeautifulSoup
import urllib3
import sqlite3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# 資料庫檔案名稱
DATABASE = 'movies.db'

def get_db():
    """取得資料庫連線"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # 讓查詢結果可以用欄位名稱存取
    return conn

def init_db():
    """初始化資料庫：建立電影資料表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            poster_url TEXT,
            detail_url TEXT,
            release_date TEXT,
            runtime TEXT,
            last_update TEXT
        )
    ''')
    conn.commit()
    conn.close()

def spider_and_save():
    """爬取開眼電影網近期上映電影，存到資料庫"""
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url, verify=False)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".filmListAllX li")
    
    # 取得更新時間
    update_tag = sp.find("div", class_="smaller09")
    last_update = update_tag.text[5:] if update_tag else datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = get_db()
    cursor = conn.cursor()
    
    # 先清空舊資料（可依需求保留或覆蓋）
    cursor.execute("DELETE FROM movies")
    
    for item in result:
        # 海報圖片
        img_tag = item.find("img")
        poster_url = img_tag.get("src") if img_tag else ""
        
        # 電影名稱
        title_tag = item.find("div", class_="filmtitle")
        title = title_tag.text.strip() if title_tag else "未知"
        
        # 電影介紹頁
        a_tag = title_tag.find("a") if title_tag else None
        detail_url = "http://www.atmovies.com.tw" + a_tag.get("href") if a_tag else ""
        
        # 上映日期與片長
        runtime_tag = item.find("div", class_="runtime")
        if runtime_tag:
            runtime_text = runtime_tag.text
            # 取出上映日期
            if "上映日期：" in runtime_text:
                date_part = runtime_text.split("上映日期：")[1].split("片長：")[0].strip()
                release_date = date_part[:10] if len(date_part) >= 10 else date_part
            else:
                release_date = "未知"
            
            # 取出片長
            if "片長：" in runtime_text:
                length_part = runtime_text.split("片長：")[1].replace("分", "").strip()
                runtime = length_part
            else:
                runtime = "未知"
        else:
            release_date = "未知"
            runtime = "未知"
        
        # 存入資料庫
        cursor.execute('''
            INSERT INTO movies (title, poster_url, detail_url, release_date, runtime, last_update)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title, poster_url, detail_url, release_date, runtime, last_update))
    
    conn.commit()
    movie_count = cursor.rowcount
    conn.close()
    
    return last_update, movie_count


@app.route("/")
def index():
    """首頁"""
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.route("/spiderMovie")
def spider_movie():
    """(1) 爬取即將上映電影，存到資料庫，顯示最近更新日期及筆數"""
    try:
        last_update, movie_count = spider_and_save()
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>爬蟲結果</title>
            <style>
                body {{ font-family: Arial; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .card {{ background: white; border-radius: 20px; padding: 40px; max-width: 500px; margin: 0 auto; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }}
                h1 {{ color: #667eea; }}
                .info {{ font-size: 1.2em; margin: 20px 0; }}
                .btn {{ display: inline-block; margin: 10px; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 25px; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>✅ 爬蟲完成！</h1>
                <div class="info">📅 最近更新日期：{last_update}</div>
                <div class="info">🎬 爬取電影數量：{movie_count} 部</div>
                <a href="/" class="btn">🏠 回首頁</a>
                <a href="/searchMovie" class="btn">🔍 前往查詢</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<p>爬蟲錯誤：{e}</p>"


@app.route("/searchMovie")
def search_movie():
    """(2) 輸入片名關鍵字，查詢資料庫符合的電影，列出：編號、片名、海報、介紹頁、上映日期"""
    
    keyword = request.args.get("keyword", "")
    
    if not keyword:
        # 顯示搜尋表單
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>搜尋電影</title>
            <style>
                body { font-family: 'Microsoft JhengHei', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; }
                .container { background: white; border-radius: 20px; padding: 40px; width: 90%; max-width: 500px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
                input { padding: 12px; width: 70%; margin: 10px; border: 1px solid #ddd; border-radius: 25px; font-size: 16px; }
                button { padding: 12px 25px; background: #667eea; color: white; border: none; border-radius: 25px; cursor: pointer; font-size: 16px; }
                button:hover { background: #764ba2; }
                h1 { color: #667eea; }
                .btn { display: inline-block; margin-top: 20px; padding: 10px 20px; background: #ccc; color: #333; text-decoration: none; border-radius: 25px; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 搜尋電影 (資料庫)</h1>
                <form method="get" action="/searchMovie">
                    <input type="text" name="keyword" placeholder="請輸入片名關鍵字，例如：超" required>
                    <br>
                    <button type="submit">搜尋</button>
                </form>
                <a href="/" class="btn">🏠 回首頁</a>
            </div>
        </body>
        </html>
        """
    
    # 從資料庫查詢
    conn = get_db()
    cursor = conn.cursor()
    
    # 使用 LIKE 進行模糊比對
    cursor.execute("SELECT * FROM movies WHERE title LIKE ? ORDER BY id", (f'%{keyword}%',))
    results = cursor.fetchall()
    conn.close()
    
    # 產生結果頁面
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>搜尋結果：{keyword}</title>
        <style>
            body {{ font-family: 'Microsoft JhengHei', Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; margin: 0; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            h1 {{ color: white; text-align: center; }}
            .movie-card {{ background: white; border-radius: 15px; padding: 20px; margin-bottom: 20px; display: flex; gap: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.2); }}
            .movie-pic img {{ width: 120px; border-radius: 10px; object-fit: cover; }}
            .movie-info {{ flex: 1; }}
            .movie-title {{ color: #667eea; margin-bottom: 10px; }}
            .movie-detail {{ color: #555; margin: 8px 0; }}
            .movie-link a {{ color: #ff6b6b; text-decoration: none; }}
            .footer {{ text-align: center; margin-top: 20px; }}
            .back-link {{ display: inline-block; margin: 10px; padding: 10px 20px; background: white; color: #667eea; text-decoration: none; border-radius: 50px; }}
            .no-result {{ background: white; border-radius: 15px; padding: 40px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 搜尋「{keyword}」的結果</h1>
    """
    
    if len(results) == 0:
        html += f"""
            <div class="no-result">
                <p>❌ 找不到包含「{keyword}」的電影</p>
                <p>請先到 <a href="/spiderMovie">爬蟲頁面</a> 爬取電影資料</p>
            </div>
        """
    else:
        for movie in results:
            html += f"""
            <div class="movie-card">
                <div class="movie-pic">
                    <img src="{movie['poster_url']}" alt="{movie['title']}" onerror="this.src='https://via.placeholder.com/120x170?text=No+Image'">
                </div>
                <div class="movie-info">
                    <h2 class="movie-title">#{movie['id']} 🎬 {movie['title']}</h2>
                    <p class="movie-detail">📅 上映日期：{movie['release_date']}</p>
                    <p class="movie-detail">⏱️ 片長：{movie['runtime']} 分鐘</p>
                    <p class="movie-link">🔗 <a href="{movie['detail_url']}" target="_blank">點我看詳細介紹</a></p>
                    <p class="movie-detail" style="font-size: 12px; color: #999;">📌 資料更新：{movie['last_update']}</p>
                </div>
            </div>
            """
    
    html += """
            <div class="footer">
                <a href="/" class="back-link">🏠 回首頁</a>
                <a href="/searchMovie" class="back-link">🔍 重新搜尋</a>
                <a href="/spiderMovie" class="back-link">🕷️ 更新資料</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


# 啟動時初始化資料庫
init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
