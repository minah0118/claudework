#!/bin/bash
echo "=========================================="
echo "  줌 영상 자동편집 - 내 컴퓨터 점검 (Mac)"
echo "  아무것도 설치하지 않고 확인만 합니다."
echo "=========================================="
echo

echo "[1] Python"
if command -v python3 >/dev/null 2>&1; then
    python3 --version
    echo "   => 설치되어 있어요."
else
    echo "   => 설치되어 있지 않아요."
fi
echo

echo "[2] ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then
    ffmpeg -version 2>&1 | head -1 | cut -d' ' -f1-3
    echo "   => 설치되어 있어요."
else
    echo "   => 설치되어 있지 않아요."
fi
echo

echo "[3] CapCut 드래프트 폴더"
DRAFT="$HOME/Movies/CapCut/User Data/Projects/com.lveditor.draft"
if [ -d "$DRAFT" ]; then
    echo "   $DRAFT"
    echo "   => 찾았어요."
else
    echo "   기본 위치에 없어요. CapCut 설정의 \"초안 위치\"를 확인해 주세요."
fi
echo
echo "=========================================="
echo " 이 창의 내용을 전부 복사해서 Claude에게 보내주세요."
echo " (Cmd+A, Cmd+C)"
echo "=========================================="
read -n 1 -s -r -p "아무 키나 누르면 창이 닫혀요."
