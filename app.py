from flask import Flask, request
import requests
from bs4 import BeautifulSoup
import urllib3
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import os
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Firebase 初始化 - 使用環境變數
def init_firebase():
    try:
        # 從環境變數取得 Firebase 憑證
        firebase_config = os.environ.get('FIREBASE_CONFIG')
        if firebase_config:
            config = json.loads(firebase_config)
            cred = credentials.Certificate(config)
        else:
            # 本地開發使用檔案
            cred = credentials.Certificate("serviceAccountKey.json")
        
        firebase_admin.initialize_app(cred, {
            'databaseURL': os.environ.get('FIREBASE_DATABASE_URL', 'https://你的專案ID.firebaseio.com/')
        })
        return True
    except Exception as e:
        print(f"Firebase 初始化失敗: {e}")
        return False

# 嘗試初始化 Firebase
firebase_available = init_firebase()

@app.route("/spiderMovie")
def spider_movie():
    """(1) 爬取即將上映電影，存到資料庫，並顯示最近更新日期及爬取電影有幾部"""
    
    if not firebase_available:
        return """
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>錯誤</title></head>
        <body style="text-align:center; padding:50px;">
            <h1>❌ Firebase 設定錯誤</h1>
            <p>請檢查環境變數設定</p>
            <a href="/">回首頁</a>
        </body>
        </html>
        """
    
    try:
        url = "http://www.atmovies.com.tw/movie/next/"
        Data = requests.get(url, verify=False, timeout=10)
        Data.encoding = "utf-8"
        sp = BeautifulSoup(Data.text, "html.parser")
        result = sp.select(".filmListAllX li")
        lastUpdate = sp.find("div", class_="smaller09").text[5:]
        
        movies = []
        idx = 1
        
        for item in result:
            # 海報圖片
            img_tag = item.find("img")
            picture = img_tag.get("src") if img_tag else ""
            
            # 電影名稱
            title_tag = item.find("div", class_="filmtitle")
            if not title_tag:
                continue
            title = title_tag.text.strip()
            
            # 電影介紹頁
            a_tag = title_tag.find("a")
            hyperlink = "http://www.atmovies.com.tw" + a_tag.get("href") if a_tag else ""
            
            # 上映日期與片長
            runtime_tag = item.find("div", class_="runtime")
            if runtime_tag:
                runtime_text = runtime_tag.text
                # 解析上映日期
                import re
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', runtime_text)
                showDate = date_match.group(1) if date_match else "未知"
                
                length_match = re.search(r'片長：(\d+)分', runtime_text)
                showLength = length_match.group(1) if length_match else "未知"
            else:
                showDate = "未知"
                showLength = "未知"
            
            movie_data = {
                "id": idx,
                "title": title,
                "poster": picture,
                "url": hyperlink,
                "release_date": showDate,
                "length": showLength,
                "crawl_time": datetime.now().isoformat()
            }
            movies.append(movie_data)
            idx += 1
        
        # 儲存到 Firebase
        ref = db.reference('/movies')
        ref.set({
            "last_update": lastUpdate,
            "count": len(movies),
            "update_time": datetime.now().isoformat(),
            "data": movies
        })
        
        # 顯示結果
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>爬蟲儲存結果</title>
            <style>
                body {{
                    font-family: 'Microsoft JhengHei', Arial, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 40px;
                    margin: 0;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                }}
                h1 {{ color: #667eea; }}
                .success {{ color: #4CAF50; font-size: 48px; }}
                .info {{ background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .info p {{ margin: 10px 0; font-size: 18px; }}
                .btn {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    padding: 12px 24px;
                    margin: 10px;
                    border-radius: 50px;
                    transition: all 0.3s ease;
                }}
                .btn:hover {{ background: #764ba2; transform: translateY(-3px); }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success">✓</div>
                <h1>✅ 爬蟲儲存成功！</h1>
                <div class="info">
                    <p>📅 最近更新日期：{lastUpdate}</p>
                    <p>🎬 爬取電影數量：{len(movies)} 部</p>
                    <p>⏰ 儲存時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                <a href="/searchMovie" class="btn">🔍 前往查詢電影</a>
                <a href="/" class="btn">🏠 回首頁</a>
            </div>
        </body>
        </html>
        """
        return html
    
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>錯誤</title></head>
        <body style="text-align:center; padding:50px;">
            <h1>❌ 爬蟲發生錯誤</h1>
            <p>錯誤訊息：{str(e)}</p>
            <a href="/">回首頁</a>
        </body>
        </html>
        """

@app.route("/searchMovie")
def search_movie():
    """(2) 輸入片名關鍵字，查詢資料庫符合的電影"""
    
    if not firebase_available:
        return """
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>錯誤</title></head>
        <body style="text-align:center; padding:50px;">
            <h1>❌ Firebase 設定錯誤</h1>
            <p>請檢查環境變數設定</p>
            <a href="/">回首頁</a>
        </body>
        </html>
        """
    
    try:
        keyword = request.args.get("keyword", "")
        
        # 從 Firebase 讀取資料
        ref = db.reference('/movies')
        data = ref.get()
        
        if not data or not data.get('data'):
            # 沒有資料時顯示警告
            return """
            <!DOCTYPE html>
            <html>
            <head><meta charset="UTF-8"><title>查詢電影</title>
            <style>
                body { font-family: Arial; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; }
                .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 20px; padding: 40px; text-align: center; }
                .btn { display: inline-block; background: #667eea; color: white; text-decoration: none; padding: 10px 20px; border-radius: 50px; margin-top: 20px; }
            </style>
            </head>
            <body>
                <div class="container">
                    <h2>⚠️ 尚無電影資料</h2>
                    <p>請先執行 <a href="/spiderMovie">爬蟲儲存</a> 取得電影資料</p>
                    <a href="/" class="btn">回首頁</a>
                </div>
            </body>
            </html>
            """
        
        movies_data = data.get('data', [])
        last_update = data.get('last_update', '未知')
        total_count = data.get('count', 0)
        
        if not keyword:
            # 顯示搜尋表單
            return f"""
            <!DOCTYPE html>
            <html lang="zh-TW">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>查詢電影</title>
                <style>
                    body {{
                        font-family: 'Microsoft JhengHei', Arial, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        padding: 40px;
                        margin: 0;
                    }}
                    .container {{
                        max-width: 800px;
                        margin: 0 auto;
                        background: white;
                        border-radius: 20px;
                        padding: 40px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    }}
                    h1 {{ color: #667eea; text-align: center; }}
                    .search-box {{
                        display: flex;
                        gap: 10px;
                        margin: 30px 0;
                    }}
                    input {{
                        flex: 1;
                        padding: 15px;
                        font-size: 16px;
                        border: 2px solid #ddd;
                        border-radius: 10px;
                    }}
                    button {{
                        padding: 15px 30px;
                        background: #667eea;
                        color: white;
                        border: none;
                        border-radius: 10px;
                        cursor: pointer;
                        font-size: 16px;
                    }}
                    button:hover {{ background: #764ba2; }}
                    .info {{ background: #e3f2fd; padding: 10px; border-radius: 10px; margin-bottom: 20px; text-align: center; }}
                    .btn {{
                        display: inline-block;
                        background: #667eea;
                        color: white;
                        text-decoration: none;
                        padding: 10px 20px;
                        border-radius: 50px;
                        margin-top: 20px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🔍 查詢電影</h1>
                    <div class="info">
                        📅 資料庫最後更新：{last_update} | 📊 共 {total_count} 部電影
                    </div>
                    <form method="get" action="/searchMovie" class="search-box">
                        <input type="text" name="keyword" placeholder="請輸入片名關鍵字，例如：蜘蛛人" required>
                        <button type="submit">🔍 搜尋</button>
                    </form>
                    <div style="text-align: center;">
                        <a href="/" class="btn">🏠 回首頁</a>
                        <a href="/spiderMovie" class="btn">🔄 重新爬取</a>
                    </div>
                </div>
            </body>
            </html>
            """
        
        # 搜尋符合條件的電影
        results = []
        for movie in movies_data:
            if keyword.lower() in movie['title'].lower():
                results.append(movie)
        
        # 顯示搜尋結果
        results_html = ""
        for movie in results:
            results_html += f"""
            <div style="border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin-bottom: 15px; display: flex; gap: 20px;">
                <div style="flex-shrink: 0;">
                    <img src="{movie['poster']}" alt="{movie['title']}" style="width: 100px; border-radius: 8px;" onerror="this.src='https://via.placeholder.com/100x150?text=No+Image'">
                </div>
                <div style="flex: 1;">
                    <h3>#{movie['id']} 🎬 {movie['title']}</h3>
                    <p>📅 上映日期：{movie['release_date']}</p>
                    <p>⏱️ 片長：{movie['length']} 分鐘</p>
                    <p>🔗 <a href="{movie['url']}" target="_blank" style="color: #667eea;">點我看詳細介紹</a></p>
                </div>
            </div>
            """
        
        if not results:
            results_html = f'<p style="text-align:center; color:#999; padding:40px;">❌ 找不到包含「{keyword}」的電影，請試試其他關鍵字</p>'
        
        html = f"""
        <!DOCTYPE html>
        <html lang="zh-TW">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>搜尋結果：{keyword}</title>
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
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }}
                h1 {{ color: #667eea; }}
                h2 {{ color: #764ba2; border-bottom: 2px solid #667eea; padding-bottom: 10px; }}
                .search-again {{
                    display: flex;
                    gap: 10px;
                    margin: 20px 0;
                }}
                .search-again input {{
                    flex: 1;
                    padding: 10px;
                    border: 2px solid #ddd;
                    border-radius: 8px;
                }}
                .search-again button {{
                    padding: 10px 20px;
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                }}
                .btn {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    padding: 10px 20px;
                    border-radius: 50px;
                    margin-top: 20px;
                    margin-right: 10px;
                }}
                .info {{
                    background: #e3f2fd;
                    padding: 10px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 搜尋結果：「{keyword}」</h1>
                <div class="info">
                    📅 資料庫最後更新：{last_update} | 找到 {len(results)} 部相關電影
                </div>
                
                <form method="get" action="/searchMovie" class="search-again">
                    <input type="text" name="keyword" placeholder="重新輸入關鍵字" value="{keyword}">
                    <button type="submit">🔍 重新搜尋</button>
                </form>
                
                <h2>📽️ 符合條件的電影：</h2>
                {results_html}
                
                <div style="margin-top: 30px; text-align: center;">
                    <a href="/searchMovie" class="btn">🔄 新搜尋</a>
                    <a href="/" class="btn">🏠 回首頁</a>
                    <a href="/spiderMovie" class="btn">🔄 重新爬取</a>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>錯誤</title></head>
        <body style="text-align:center; padding:50px;">
            <h1>❌ 查詢發生錯誤</h1>
            <p>錯誤訊息：{str(e)}</p>
            <a href="/">回首頁</a>
        </body>
        </html>
        """

# 保留原有的路由
@app.route("/movie")
def movie():
    """爬取開眼電影網近期上映電影，直接顯示在網頁上"""
    
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url, verify=False)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".filmListAllX li")
    lastUpdate = sp.find("div", class_="smaller09").text[5:]

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
        img_tag = item.find("img")
        picture = img_tag.get("src") if img_tag else ""
        
        title_tag = item.find("div", class_="filmtitle")
        title = title_tag.text if title_tag else "未知"
        
        a_tag = title_tag.find("a") if title_tag else None
        hyperlink = "http://www.atmovies.com.tw" + a_tag.get("href") if a_tag else ""
        
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

@app.route("/search")
def search():
    """即時搜尋電影（不依賴資料庫）- 保留原有功能"""
    
    keyword = request.args.get("keyword", "")
    
    if not keyword:
        return """
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>搜尋電影</title></head>
        <body style="text-align:center; padding:50px;">
            <h1>🔍 請輸入關鍵字</h1>
            <form method="get" action="/search">
                <input type="text" name="keyword" placeholder="例如：超" style="padding:10px;width:200px;">
                <button type="submit" style="padding:10px 20px;">搜尋</button>
            </form>
            <br><a href="/">回首頁</a>
        </body>
        </html>
        """
    
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url, verify=False)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".filmListAllX li")
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>搜尋結果：{keyword}</title>
    <style>
        body {{ font-family: Arial; background: #f0f0f0; padding: 40px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .result {{ background: white; border-radius: 10px; padding: 15px; margin-bottom: 15px; }}
        h1 {{ color: #667eea; }}
        a {{ color: #667eea; }}
    </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 搜尋「{keyword}」的結果</h1>
    """
    
    found = False
    for item in result:
        title_tag = item.find("div", class_="filmtitle")
        title = title_tag.text if title_tag else ""
        
        if keyword in title:
            found = True
            a_tag = title_tag.find("a") if title_tag else None
            hyperlink = "http://www.atmovies.com.tw" + a_tag.get("href") if a_tag else ""
            
            runtime_tag = item.find("div", class_="runtime")
            if runtime_tag:
                show = runtime_tag.text.replace("上映日期：", "").replace("片長：", "").replace("分", "")
                showDate = show[0:10] if len(show) >= 10 else "未知"
                showLength = show[13:] if len(show) > 13 else "未知"
            else:
                showDate = "未知"
                showLength = "未知"
            
            html += f"""
            <div class="result">
                <h3>🎬 {title}</h3>
                <p>📅 上映日期：{showDate}</p>
                <p>⏱️ 片長：{showLength} 分鐘</p>
                <p>🔗 <a href="{hyperlink}" target="_blank">詳細介紹</a></p>
            </div>
            """
    
    if not found:
        html += f"<p>❌ 找不到包含「{keyword}」的電影</p>"
    
    html += '<br><a href="/">回首頁</a> | <a href="/searchMovie">改用資料庫查詢</a>'
    html += "</div></body></html>"
    return html

@app.route("/")
def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# 為了 Vercel 部署需要
app = app

if __name__ == "__main__":
    app.debug = True
    app.run()
