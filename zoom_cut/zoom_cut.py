"""긴 줌 영상에서 원하는 구간만 골라 이어 붙인 CapCut 드래프트를 만듭니다.

사용법
  1. 같은 폴더의 '구간.txt'에 남기고 싶은 구간을 적어요.
  2. '실행.bat'을 더블클릭하고, 영상 파일을 창에 끌어다 놓은 뒤 Enter를 눌러요.
  3. CapCut을 열면 새 드래프트가 생겨 있어요.
"""

import os
import re
import sys
from datetime import datetime

import pycapcut as cc

# ── 설정 ─────────────────────────────────────────────
# CapCut 드래프트 폴더 (CapCut 설정의 "초안 위치"와 같아야 해요)
DRAFT_FOLDER = os.path.expandvars(
    r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"
)
# 구간 목록 파일 (이 스크립트와 같은 폴더)
RANGES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "구간.txt")
# ────────────────────────────────────────────────────

SEC = 1_000_000  # pyCapCut은 시간을 마이크로초 단위로 다뤄요


def parse_time(text: str) -> int:
    """'1:02:03', '02:03', '123' 같은 글자를 마이크로초로 바꿔요."""
    parts = text.strip().split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"시간 형식이 이상해요: '{text}'")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return int(round(seconds * SEC))


def format_time(us: int) -> str:
    total = us // SEC
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def read_ranges(path: str) -> list[tuple[int, int]]:
    """구간.txt를 읽어 (시작, 끝) 목록을 돌려줘요. 적힌 순서 그대로 이어 붙여요."""
    ranges = []
    with open(path, encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            pieces = re.split(r"\s*[~\-]\s*", line)
            if len(pieces) != 2:
                raise ValueError(f"{line_no}번째 줄을 읽을 수 없어요: '{line}'\n"
                                 "  '시작 ~ 끝' 모양으로 적어 주세요. 예) 00:05:30 ~ 00:12:00")
            start, end = parse_time(pieces[0]), parse_time(pieces[1])
            if end <= start:
                raise ValueError(f"{line_no}번째 줄: 끝 시간이 시작 시간보다 빨라요: '{line}'")
            ranges.append((start, end))
    if not ranges:
        raise ValueError("구간.txt에 구간이 하나도 없어요.")
    return ranges


def main() -> None:
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        video_path = input("영상 파일을 이 창에 끌어다 놓고 Enter를 누르세요:\n> ")
    video_path = video_path.strip().strip('"')
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"영상 파일을 찾을 수 없어요: {video_path}")
    if not os.path.isdir(DRAFT_FOLDER):
        raise FileNotFoundError(f"CapCut 드래프트 폴더를 찾을 수 없어요: {DRAFT_FOLDER}")

    ranges = read_ranges(RANGES_FILE)

    print("\n영상 정보를 읽는 중...")
    material = cc.VideoMaterial(video_path)
    print(f"  길이 {format_time(material.duration)}, 화면 {material.width}x{material.height}")

    for start, end in ranges:
        if start >= material.duration:
            raise ValueError(f"구간 {format_time(start)} ~ {format_time(end)}이(가) "
                             f"영상 길이({format_time(material.duration)})를 넘어요.")

    draft_name = "줌편집_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    script = cc.DraftFolder(DRAFT_FOLDER).create_draft(draft_name, material.width, material.height)
    script.add_track(cc.TrackType.video)

    position = 0  # 새 영상에서 다음 조각이 놓일 위치
    print("\n이어 붙이는 구간:")
    for i, (start, end) in enumerate(ranges, start=1):
        end = min(end, material.duration)
        length = end - start
        script.add_segment(cc.VideoSegment(
            material,
            cc.Timerange(position, length),
            source_timerange=cc.Timerange(start, length),
        ))
        print(f"  {i}. {format_time(start)} ~ {format_time(end)}  ({format_time(length)})")
        position += length

    script.save()
    print(f"\n완성! 전체 길이 {format_time(position)}")
    print(f"CapCut을 열고 '{draft_name}' 드래프트를 확인하세요.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[오류] {e}")
        sys.exit(1)
