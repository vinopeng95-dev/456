from flask import Flask, request
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
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化資料庫"""
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
    """爬取並存入資料庫，同時回傳資料用於顯示"""
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
    
    # 清空舊資料
    cursor.execute("DELETE FROM movies")
    
    movies_list = []  # 用於存儲電影資料，同時回傳顯示
    
    for idx, item in enumerate(result, 1):
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
            if "上映日期：" in runtime_text:
                date_part = runtime_text.split("上映日期：")[1].split("片長：")[0].strip()
                release_date = date_part[:10] if len(date_part) >= 10 else date_part
            else:
                release_date = "未知"
            
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
        
        # 同時存入列表用於顯示
        movies_list.append({
            "id": idx,
            "title": title,
            "poster_url": poster_url,
            "detail_url": detail_url,
            "release_date": release_date,
            "runtime": runtime
        })
    
    conn.commit()
    movie_count = len(movies_list)
    conn.close()
    
    return last_update, movie_count, movies_list


@app.route("/")
def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.route("/movie")
def movie():
    """保留原有功能：爬取開眼電影網近期上映電影，直接顯示在網頁上"""
    
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url, verify=False)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".filmListAllX li")
    lastUpdate = sp.find("div", class_="smaller09").text[5:]

    # 開始產生 HTML 結果
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <title>近期上映電影</title>
        <style>
            body {{
                font-family: 'Microsoft JhengHei', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 40px;
                margin: 0;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
            }}
            h1 {{
                color: white;
                text-align: center;
                margin-bottom: 10px;
            }}
            .update-info {{
                color: white;
                text-align: center;
                margin-bottom: 30px;
                opacity: 0.9;
            }}
            .movie-card {{
                background: white;
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
                display: flex;
                gap: 20px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }}
            .movie-pic img {{
                width: 120px;
                border-radius: 10px;
            }}
            .movie-info {{
                flex: 1;
            }}
            .movie-title {{
                color: #667eea;
                margin-bottom: 10px;
            }}
            .movie-detail {{
                color: #555;
                margin: 8px 0;
            }}
            .movie-link a {{
                color: #ff6b6b;
                text-decoration: none;
            }}
            .back-link {{
                display: inline-block;
                margin: 20px 10px;
                padding: 10px 20px;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 50px;
            }}
            .footer {{
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 近期上映電影</h1>
            <div class="update-info">📅 資料更新時間：{lastUpdate}</div>
    """

    for item in result:
        # 海報圖片
        img_tag = item.find("img")
        picture = img_tag.get("src") if img_tag else ""
        
        # 電影名稱
        title_tag = item.find("div", class_="filmtitle")
        title = title_tag.text if title_tag else "未知"
        
        # 電影介紹頁
        a_tag = title_tag.find("a") if title_tag else None
        hyperlink = "http://www.atmovies.com.tw" + a_tag.get("href") if a_tag else ""
        
        # 上映日期與片長
        runtime_tag = item.find("div", class_="runtime")
        if runtime_tag:
            show = runtime_tag.text.replace("上映日期：", "").replace("片長：", "").replace("分", "")
            showDate = show[0:10] if len(show) >= 10 else "未知"
            showLength = show[13:] if len(show) > 13 else "未知"
        else:
            showDate = "未知"
            showLength = "未知"

        html += f"""
            <div class="movie-card">
                <div class="movie-pic">
                    <img src="{picture}" alt="{title}">
                </div>
                <div class="movie-info">
                    <h2 class="movie-title">🎬 {title}</h2>
                    <p class="movie-detail">📅 上映日期：{showDate}</p>
                    <p class="movie-detail">⏱️ 片長：{showLength} 分鐘</p>
                    <p class="movie-link">🔗 <a href="{hyperlink}" target="_blank">點我看詳細介紹</a></p>
                </div>
            </div>
        """

    html += """
            <div class="footer">
                <a href="/" class="back-link">🏠 回首頁</a>
                <a href="/searchMovie" class="back-link">🔍 搜尋電影</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


@app.route("/spiderMovie")
def spider_movie():
    """(1) 爬取即將上映電影，存到資料庫，並顯示結果"""
    try:
        last_update, movie_count, movies_list = spider_and_save()
        
        # 產生顯示頁面（類似原本的 /movie 但加上資料庫儲存成功的訊息）
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <title>爬蟲結果 - 已存入資料庫</title>
            <style>
                body {{
                    font-family: 'Microsoft JhengHei', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 40px;
                    margin: 0;
                }}
                .container {{
                    max-width: 900px;
                    margin: 0 auto;
                }}
                h1 {{
                    color: white;
                    text-align: center;
                    margin-bottom: 10px;
                }}
                .update-info {{
                    color: white;
                    text-align: center;
                    margin-bottom: 30px;
                    opacity: 0.9;
                }}
                .success-badge {{
                    background: #4CAF50;
                    color: white;
                    text-align: center;
                    padding: 10px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
                .movie-card {{
                    background: white;
                    border-radius: 15px;
                    padding: 20px;
                    margin-bottom: 20px;
                    display: flex;
                    gap: 20px;
                    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                }}
                .movie-pic img {{
                    width: 120px;
                    border-radius: 10px;
                }}
                .movie-info {{
                    flex: 1;
                }}
                .movie-title {{
                    color: #667eea;
                    margin-bottom: 10px;
                }}
                .movie-detail {{
                    color: #555;
                    margin: 8px 0;
                }}
                .movie-link a {{
                    color: #ff6b6b;
                    text-decoration: none;
                }}
                .back-link {{
                    display: inline-block;
                    margin: 20px 10px;
                    padding: 10px 20px;
                    background: white;
                    color: #667eea;
                    text-decoration: none;
                    border-radius: 50px;
                }}
                .footer {{
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ 爬蟲完成並存入資料庫</h1>
                <div class="success-badge">
                    📅 最近更新日期：{last_update} | 🎬 共 {movie_count} 部電影
                </div>
        """
        
        for movie in movies_list:
            html += f"""
            <div class="movie-card">
                <div class="movie-pic">
                    <img src="{movie['poster_url']}" alt="{movie['title']}">
                </div>
                <div class="movie-info">
                    <h2 class="movie-title">#{movie['id']} 🎬 {movie['title']}</h2>
                    <p class="movie-detail">📅 上映日期：{movie['release_date']}</p>
                    <p class="movie-detail">⏱️ 片長：{movie['runtime']} 分鐘</p>
                    <p class="movie-link">🔗 <a href="{movie['detail_url']}" target="_blank">點我看詳細介紹</a></p>
                </div>
            </div>
            """
        
        html += """
            <div class="footer">
                <a href="/" class="back-link">🏠 回首頁</a>
                <a href="/searchMovie" class="back-link">🔍 搜尋電影(資料庫)</a>
                <a href="/movie" class="back-link">🎬 即時爬蟲顯示</a>
            </div>
        </div>
    </body>
    </html>
        """
        return html
        
    except Exception as e:
        return f"<p>爬蟲錯誤：{e}</p>"


@app.route("/searchMovie")
def search_movie():
    """(2) 從資料庫查詢電影"""
    
    keyword = request.args.get("keyword", "")
    
    if not keyword:
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
                <h1>🔍 從資料庫搜尋電影</h1>
                <form method="get" action="/searchMovie">
                    <input type="text" name="keyword" placeholder="請輸入片名關鍵字，例如：超" required>
                    <br>
                    <button type="submit">搜尋</button>
                </form>
                <a href="/" class="btn">🏠 回首頁</a>
                <a href="/spiderMovie" class="btn">🕷️ 先爬取資料</a>
            </div>
        </body>
        </html>
        """
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM movies WHERE title LIKE ? ORDER BY id", (f'%{keyword}%',))
    results = cursor.fetchall()
    conn.close()
    
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
                </div>
            </div>
            """
    
    html += """
            <div class="footer">
                <a href="/" class="back-link">🏠 回首頁</a>
                <a href="/searchMovie" class="back-link">🔍 重新搜尋</a>
                <a href="/spiderMovie" class="back-link">🕷️ 更新資料</a>
                <a href="/movie" class="back-link">🎬 即時爬蟲</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


# 初始化資料庫
init_db()

if __name__ == "__main__":
    app.run(debug=True)
