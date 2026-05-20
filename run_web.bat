@echo off
echo 연합뉴스 웹 오디오 리더기 서버를 시작합니다...
echo 브라우저가 자동으로 열립니다. (혹은 http://localhost:5000 으로 접속하세요)

start http://localhost:5000
C:\Users\MBC\AppData\Local\Programs\Python\Python311\python.exe app.py
pause
