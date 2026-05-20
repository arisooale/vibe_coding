from flask import Flask, render_template, jsonify
import requests
from bs4 import BeautifulSoup
import feedparser
import re

app = Flask(__name__)

# 연합뉴스 최신 속보 RSS URL
RSS_URL = 'https://www.yna.co.kr/rss/news.xml'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def clean_text(text):
    """기사 본문에서 불필요한 광고, 이메일 등을 제거합니다."""
    if not text:
        return ""
    
    # 1. (서울=연합뉴스) 홍길동 기자 = 패턴 제거
    text = re.sub(r'^\([^)]+\)\s*.*?기자\s*=\s*', '', text)
    text = re.sub(r'\[연합뉴스[^\]]*\]', '', text)
    
    # 2. 이메일 주소 제거
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
    
    # 3. 상투적 문구 제거
    remove_list = [
        '제보는 카카오톡 okjebo',
        '<저작권자(c) 연합뉴스, 무단 전재-재배포, AI 학습 및 활용 금지>',
        '무단 전재 및 재배포 금지',
        '무단 전재-재배포 금지'
    ]
    for r in remove_list:
        text = text.replace(r, '')
        
    text = re.sub(r'[가-힣]{2,4}\s*기자$', '', text)
    
    # 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def scrape_article(url):
    """기사 페이지에 접속하여 본문만 추출합니다."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 기사 본문 영역
        article_body = soup.find('article', class_='story-news')
        if not article_body:
            article_body = soup.find('div', class_='article')
            
        if not article_body:
            return ""
            
        # 사진 설명, 광고 제거
        for tag in article_body.select('figcaption, p.caption, .image-zone, .article-img, .ad'):
            tag.decompose()
            
        paragraphs = article_body.find_all('p')
        content = " ".join([p.get_text() for p in paragraphs])
        
        return clean_text(content)
    except Exception as e:
        print(f"Scraping error for {url}: {e}")
        return ""

@app.route('/')
def index():
    """웹 프론트엔드 화면 제공"""
    return render_template('index.html')

@app.route('/api/news')
def get_news():
    """RSS 피드를 파싱하여 최신 기사 10개를 JSON으로 반환"""
    try:
        feed = feedparser.parse(RSS_URL)
        articles = []
        
        # 최신 기사 10개만 가져옴 (속도 향상을 위해)
        for entry in feed.entries[:10]:
            content = scrape_article(entry.link)
            if content:
                articles.append({
                    'title': entry.title,
                    'link': entry.link,
                    'content': content
                })
        
        return jsonify({'status': 'success', 'articles': articles})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
