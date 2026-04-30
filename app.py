from flask import Flask, request
import requests
from bs4 import BeautifulSoup
import urllib3
from datetime import datetime
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# 使用全域變數儲存電影資料（Vercel 環境可用）
movies_cache = {
    "data": [],
    "last_update": "",
    "count": 0
}

def spider_movies():
    """爬取開眼電影網近期上映電影"""
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url, verify=False)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".filmListAllX li")
    
    # 取得更新時間
    update_tag = sp.find("div", class_="smaller09")
    last_update = update_tag.text[5:] if update_tag else datetime.now().strftime("%Y-%m-%d %H:%M")
    
    movies = []
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
        
        movies.append({
            "id": idx,
            "title": title,
            "poster_url": poster_url,
            "detail_url": detail_url,
            "release_date": release_date,
            "runtime": runtime
        })
    
    return last_update, movies


@app.route("/")
def index():
    """首頁"""
    return """
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>電影爬蟲系統 - 靜宜大學資管系</title>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Microsoft JhengHei', Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 0;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
            }

            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 50px;
                max-width: 600px;
                width: 90%;
                text-align: center;
            }

            h1 {
                color: #667eea;
                font-size: 2.5em;
                margin-bottom: 10px;
            }

            .subtitle {
                color: #666;
                font-size: 1em;
                margin-bottom: 30px;
                border-bottom: 2px solid #667eea;
                display: inline-block;
                padding-bottom: 5px;
            }

            h2 {
                color: #333;
                margin-bottom: 30px;
                font-size: 1.3em;
            }

            .btn {
                display: block;
                background: #667eea;
                color: white;
                text-decoration: none;
                padding: 15px 30px;
                margin: 20px 0;
                border-radius: 50px;
                font-size: 1.1em;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
            }

            .btn:hover {
                background: #764ba2;
                transform: translateY(-3px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
            }

            .btn-secondary {
                background: #ff6b6b;
                box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
            }

            .btn-secondary:hover {
                background: #ee5a52;
            }

            .btn-green {
                background: #4CAF50;
                box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
            }

            .btn-green:hover {
                background: #45a049;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🕷️ 網路爬蟲</h1>
            <div class="subtitle">靜宜大學資管系 彭韋諾</div>
            
            <h2>🎬 開眼電影網 - 電影爬蟲系統</h2>
            
            <a href="/movie" class="btn">🎬 即時爬蟲顯示電影</a>
            <a href="/spiderMovie" class="btn btn-green">💾 (1) 爬取並儲存電影</a>
            <a href="/searchMovie" class="btn btn-secondary">🔍 (2) 搜尋電影</a>
        </div>
    </body>
    </html>
    """


@app.route("/movie")
def movie():
    """即時爬蟲：直接顯示近期上映電影"""
    
    try:
        last_update, movies = spider_movies()
        
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
                <div class="update-info">📅 資料更新時間：{last_update}</div>
        """
        
        for movie in movies:
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
                <a href="/spiderMovie" class="back-link">💾 儲存到快取</a>
                <a href="/searchMovie" class="back-link">🔍 搜尋電影</a>
            </div>
        </div>
        </body>
        </html>
        """
        return html
    
    except Exception as e:
        return f"<p>爬蟲錯誤：{e}</p>"


@app.route("/spiderMovie")
def spider_movie():
    """(1) 爬取即將上映電影，儲存到記憶體快取，顯示最近更新日期及筆數"""
    global movies_cache
    
    try:
        last_update, movies = spider_movies()
        
        # 儲存到快取
        movies_cache = {
            "data": movies,
            "last_update": last_update,
            "count": len(movies)
        }
        
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
                <h1>✅ 爬蟲完成並儲存！</h1>
                <div class="info">📅 最近更新日期：{last_update}</div>
                <div class="info">🎬 儲存電影數量：{len(movies)} 部</div>
                <a href="/" class="btn">🏠 回首頁</a>
                <a href="/searchMovie" class="btn">🔍 前往查詢</a>
                <a href="/movie" class="btn">🎬 即時爬蟲</a>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<p>爬蟲錯誤：{e}</p>"


@app.route("/searchMovie")
def search_movie():
    """(2) 從快取中搜尋電影，列出：編號、片名、海報、介紹頁、上映日期"""
    
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
                .info { color: #666; margin: 10px 0; }
                .btn { display: inline-block; margin-top: 20px; padding: 10px 20px; background: #4CAF50; color: white; text-decoration: none; border-radius: 25px; }
                .btn-gray { background: #ccc; color: #333; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 從快取搜尋電影</h1>
                <div class="info">📌 請先點擊「爬取並儲存電影」建立資料</div>
                <form method="get" action="/searchMovie">
                    <input type="text" name="keyword" placeholder="請輸入片名關鍵字，例如：超" required>
                    <br>
                    <button type="submit">搜尋</button>
                </form>
                <a href="/" class="btn btn-gray">🏠 回首頁</a>
                <a href="/spiderMovie" class="btn">🕷️ 先爬取資料</a>
            </div>
        </body>
        </html>
        """
    
    # 從快取查詢
    global movies_cache
    
    if not movies_cache["data"]:
        return """
        <div style="text-align:center; padding:50px;">
            <h2>⚠️ 暫無資料</h2>
            <p>請先前往 <a href="/spiderMovie">爬蟲頁面</a> 爬取電影資料</p>
            <a href="/">回首頁</a>
        </div>
        """
    
    # 模糊比對
    results = [movie for movie in movies_cache["data"] if keyword in movie['title']]
    
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
            .update-info {{ color: white; text-align: center; margin-bottom: 20px; opacity: 0.9; }}
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
            <div class="update-info">📅 資料快取時間：{movies_cache['last_update']} | 共 {movies_cache['count']} 部電影</div>
    """
    
    if len(results) == 0:
        html += f"""
            <div class="no-result">
                <p>❌ 找不到包含「{keyword}」的電影</p>
                <p>請嘗試其他關鍵字，或 <a href="/spiderMovie">重新爬取資料</a></p>
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


# Vercel 需要這個
app.debug = False
