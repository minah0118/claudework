@echo off
chcp 65001 > nul
echo ==========================================
echo   줌 영상 자동편집 - 내 컴퓨터 점검 (Windows)
echo   아무것도 설치하지 않고 확인만 합니다.
echo ==========================================
echo.

echo [1] Python
where python > nul 2>&1
if %errorlevel%==0 (
    python --version
    echo    =^> 설치되어 있어요.
) else (
    echo    =^> 설치되어 있지 않아요.
)
echo.

echo [2] ffmpeg
where ffmpeg > nul 2>&1
if %errorlevel%==0 (
    for /f "tokens=1-3" %%a in ('ffmpeg -version 2^>^&1 ^| findstr /b "ffmpeg"') do echo    %%a %%b %%c
    echo    =^> 설치되어 있어요.
) else (
    echo    =^> 설치되어 있지 않아요.
)
echo.

echo [3] CapCut 드래프트 폴더
set "DRAFT=%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"
if exist "%DRAFT%" (
    echo    %DRAFT%
    echo    =^> 찾았어요.
) else (
    echo    기본 위치에 없어요. CapCut 설정의 "초안 위치"를 확인해 주세요.
)
echo.
echo ==========================================
echo  이 창의 내용을 전부 복사해서 Claude에게 보내주세요.
echo  (창에서 마우스 오른쪽 클릭 또는 Ctrl+A, Ctrl+C)
echo ==========================================
pause
