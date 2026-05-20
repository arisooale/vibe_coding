import os
import time
import re
import requests
from bs4 import BeautifulSoup
from gtts import gTTS
import pygame
import feedparser
import tempfile

# 초기화
pygame.mixer.init()

# 이미 읽은 기사를 추적하기 위한 집합
read_articles = set()

# RSS 피드 URL (최신 속보 전체)
RSS_URL = 'https://www.yna.co.kr/rss/news.xml'

# 헤더 (크롤링 차단 우회용)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def clean_text(text):
    """
    기사 본문에서 불필요한 부분을 제거합니다.
    """
    # 1. (서울=연합뉴스) 홍길동 기자 = 와 같은 패턴 제거
    text = re.sub(r'^\([^)]+\)\s*.*?기자\s*=\s*', '', text)
    text = re.sub(r'\[연합뉴스[^\]]*\]', '', text)
    
    # 2. 이메일 주소 제거
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
    
    # 3. 기자 이름 및 불필요한 문구 제거
    text = re.sub(r'[가-힣]{2,4}\s*기자', '', text)
    text = text.replace('제보는 카카오톡 okjebo', '')
    text = re.sub(r'<저작권자\(c\)[^>]*>[\s\S]*', '', text)
    text = re.sub(r'\d{4}\/\d{2}\/\d{2}\s+\d{2}:\d{2}\s+송고.*', '', text)
    text = text.replace('무단 전재 및 재배포 금지', '')
    text = text.replace('무단 전재-재배포 금지', '')
    
    # 여러 줄바꿈 및 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def scrape_article(url):
    """
    기사 URL에서 본문 텍스트를 추출합니다.
    """
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 본문 영역 찾기 (연합뉴스의 일반적인 기사 본문 태그 클래스)
        article_body = soup.find('article', class_='story-news')
        if not article_body:
            # 다른 클래스로 되어있는 경우 대비
            article_body = soup.find('div', class_='article')
            
        if not article_body:
            print(f"기사 본문을 찾을 수 없습니다: {url}")
            return None
            
        # 사진 설명 및 불필요한 요소 제거
        for tag in article_body.select('figcaption, p.caption, .image-zone, .article-img, .ad'):
            tag.decompose()
            
        # 단락(p) 텍스트 수집
        paragraphs = article_body.find_all('p')
        content = [p.get_text() for p in paragraphs]
        
        full_text = " ".join(content)
        cleaned_text = clean_text(full_text)
        
        return cleaned_text
        
    except Exception as e:
        print(f"크롤링 오류 ({url}): {e}")
        return None

def play_audio(text):
    """
    텍스트를 TTS로 변환하고 오디오로 재생합니다.
    """
    if not text:
        return
        
    try:
        # TTS 생성
        tts = gTTS(text=text, lang='ko')
        
        # 임시 파일로 저장
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, 'temp_news_audio.mp3')
        
        # 만약 기존 임시 파일이 있다면 삭제
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
                
        tts.save(temp_path)
        
        # 재생
        pygame.mixer.music.load(temp_path)
        pygame.mixer.music.play()
        
        # 재생이 끝날 때까지 대기
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        # 재생 완료 후 스트림 해제 (파일 삭제를 위해)
        pygame.mixer.music.unload()
        
        # 약간의 대기 (파일 잠금 해제 시간)
        time.sleep(1)
        
        # 임시 파일 삭제
        try:
            os.remove(temp_path)
        except OSError:
            pass
            
    except Exception as e:
        print(f"오디오 재생 오류: {e}")

def main():
    print("연합뉴스 오디오 리더기를 시작합니다...")
    print("최신 기사를 가져오는 중입니다. 종료하려면 Ctrl+C를 누르세요.\n")
    
    while True:
        try:
            # RSS 피드 가져오기
            feed = feedparser.parse(RSS_URL)
            
            if not feed.entries:
                print("새로운 기사를 찾을 수 없습니다. 1분 후 다시 시도합니다...")
                time.sleep(60)
                continue
                
            # 최신 기사 순서대로 정렬 (보통 RSS는 이미 정렬되어 있음)
            # RSS 피드에서 새 기사들을 찾아 거꾸로(가장 오래된 것부터 최신으로) 읽지 않고,
            # 여기서는 새로운 기사만 최신부터 읽습니다.
            
            # 새로 발견된 기사 리스트
            new_articles = []
            for entry in feed.entries:
                if entry.link not in read_articles:
                    new_articles.append(entry)
            
            # 가져온 새 기사가 있다면, 과거 기사부터 순서대로 읽거나(reverse) 그냥 순서대로 읽기
            # 사용자 요청: 최신 기사 순서대로 읽어줘 -> RSS 순서대로 (최신 -> 이전)
            for entry in new_articles:
                print(f"\n[기사 제목] {entry.title}")
                print(f"가져오는 중: {entry.link}")
                
                # 기사 본문 가져오기
                content = scrape_article(entry.link)
                
                if content:
                    # 제목 먼저 읽기
                    print("제목 재생 중...")
                    play_audio("다음 기사입니다. " + entry.title)
                    time.sleep(1)
                    
                    # 본문 읽기
                    print("본문 재생 중...")
                    play_audio(content)
                    
                # 읽은 기사로 등록
                read_articles.add(entry.link)
                
                # 다음 기사 재생 전 약간의 대기
                time.sleep(2)
                
            if not new_articles:
                print("현재 모든 기사를 읽었습니다. 1분 후 새 기사를 확인합니다...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            print("\n프로그램을 종료합니다.")
            break
        except Exception as e:
            print(f"프로그램 실행 중 오류 발생: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
