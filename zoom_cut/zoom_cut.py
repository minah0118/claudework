"""긴 줌 영상에서 원하는 구간만 골라 이어 붙인 CapCut 드래프트를 만듭니다.

하는 일
  1. '구간.txt'에 적은 구간만 남겨요.
  2. 그 안에서 소리가 없는 부분을 자동으로 잘라내요.
  3. 구간과 구간 사이에 부드러운 전환 효과를 넣어요.
  4. 영상의 처음은 서서히 나타나고, 끝은 서서히 사라지게 해요.
  5. 재생 속도를 빠르게 해요.
  6. 말한 내용을 인식해서 자막을 넣어요.

사용법
  1. 같은 폴더의 '구간.txt'에 남기고 싶은 구간을 적어요.
  2. '실행.bat'을 더블클릭하고, 영상 파일을 창에 끌어다 놓은 뒤 Enter를 눌러요.
  3. CapCut을 열면 새 드래프트가 생겨 있어요.
"""

import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime

import pycapcut as cc

# ── 설정 (원하는 대로 숫자를 바꿔 보세요) ─────────────────
# CapCut 드래프트 폴더 (CapCut 설정의 "초안 위치"와 같아야 해요)
DRAFT_FOLDER = os.path.expandvars(
    r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"
)
# 구간 목록 파일 (이 스크립트와 같은 폴더)
RANGES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "구간.txt")

# [무음 자르기]
CUT_SILENCE = True        # False로 바꾸면 무음을 자르지 않아요
SILENCE_DB = -35          # 이보다 작은 소리는 '무음'으로 봐요 (-40이면 더 조용해야 무음, -30이면 덜 조용해도 무음)
SILENCE_MIN_SEC = 0.8     # 무음이 이 시간(초) 이상 이어질 때만 잘라요
PADDING_SEC = 0.2         # 말 앞뒤로 이만큼(초)은 남겨서 말이 뚝 끊기지 않게 해요

# [전환 효과]
TRANSITION = True         # 구간.txt의 구간과 구간 사이에 전환 효과를 넣어요
TRANSITION_SEC = 0.5      # 전환 효과 길이(초)

# [인트로/아웃트로 페이드]
FADE = True               # 영상 처음은 서서히 나타나고, 끝은 서서히 사라져요
FADE_SEC = 1.0            # 페이드 길이(초)

# [속도]
SPEED = 1.2               # 1.0 = 원래 속도, 1.2 = 1.2배 빠르게, 1.5 = 1.5배 빠르게

# [자막]
SUBTITLES = False         # True로 바꾸면 자막을 자동으로 넣어요 (faster-whisper 설치 필요, 오래 걸려요)
WHISPER_MODEL = "small"   # "small" = 빠름, "medium" = 더 정확하지만 느림
SUBTITLE_SIZE = 7.0       # 자막 글자 크기
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


def find_silences(video_path: str, start: int, end: int) -> list[tuple[int, int]]:
    """ffmpeg로 [start, end] 안의 무음 구간을 찾아 원본 영상 기준 시간으로 돌려줘요."""
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-ss", f"{start / SEC:.3f}", "-t", f"{(end - start) / SEC:.3f}",
        "-i", video_path, "-vn",
        "-af", f"silencedetect=noise={SILENCE_DB}dB:d={SILENCE_MIN_SEC}",
        "-f", "null", "-",
    ]
    log = subprocess.run(cmd, capture_output=True, text=True,
                         encoding="utf-8", errors="replace").stderr
    silences = []
    silence_start = None
    for m in re.finditer(r"silence_(start|end): (-?[\d.]+)", log):
        t = start + int(float(m.group(2)) * SEC)
        if m.group(1) == "start":
            silence_start = max(t, start)
        elif silence_start is not None:
            silences.append((silence_start, min(t, end)))
            silence_start = None
    if silence_start is not None:  # 구간 끝까지 무음이 이어지는 경우
        silences.append((silence_start, end))
    return silences


def keep_pieces(start: int, end: int, silences: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """구간에서 무음을 빼고 남길 조각들을 돌려줘요. 말 앞뒤로 PADDING_SEC만큼 여유를 둬요."""
    pad = int(PADDING_SEC * SEC)
    pieces = []
    cursor = start
    for s, e in silences:
        cut_from, cut_to = s + pad, e - pad
        if cut_to - cut_from <= 0:
            continue
        if cut_from > cursor:
            pieces.append((cursor, cut_from))
        cursor = max(cursor, cut_to)
    if cursor < end:
        pieces.append((cursor, end))
    # 너무 짧은 조각(0.3초 미만)은 버려요
    return [(s, e) for s, e in pieces if e - s >= 0.3 * SEC]


def transcribe(video_path: str, start: int, end: int, model) -> list[tuple[int, int, str]]:
    """[start, end] 구간의 말을 글자로 바꿔 (시작, 끝, 문장) 목록을 원본 영상 기준 시간으로 돌려줘요."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "audio.wav")
        subprocess.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{start / SEC:.3f}", "-t", f"{(end - start) / SEC:.3f}",
            "-i", video_path, "-vn", "-ac", "1", "-ar", "16000", wav,
        ], check=True)
        segments, _ = model.transcribe(wav, language="ko", vad_filter=True)
        return [(start + int(seg.start * SEC), start + int(seg.end * SEC), seg.text.strip())
                for seg in segments if seg.text.strip()]


def to_timeline(t: int, placed: list[tuple[int, int, int]], side: str) -> int | None:
    """원본 영상의 시간 t가 완성 영상의 몇 초에 오는지 계산해요.

    placed는 (원본 시작, 원본 끝, 완성 영상에서의 시작) 목록이에요.
    t가 잘려 나간 무음 안에 있으면, 시작 시간은 다음 조각의 처음으로, 끝 시간은 앞 조각의 끝으로 맞춰요.
    """
    for src_start, src_end, tgt_start in placed:
        if src_start <= t <= src_end:
            return tgt_start + round((t - src_start) / SPEED)
    if side == "start":
        later = [p for p in placed if p[0] > t]
        return min(later)[2] if later else None
    earlier = [p for p in placed if p[1] < t]
    if not earlier:
        return None
    src_start, src_end, tgt_start = max(earlier, key=lambda p: p[1])
    return tgt_start + round((src_end - src_start) / SPEED)


def load_whisper():
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("\n[알림] 자막 기능을 쓰려면 faster-whisper가 필요해요. 명령 프롬프트에서 아래를 실행해 주세요.")
        print("   python -m pip install faster-whisper")
        print("   (이번에는 자막 없이 만들게요.)")
        return None
    print(f"\n음성 인식 모델({WHISPER_MODEL})을 준비하는 중... 처음 한 번은 내려받느라 몇 분 걸려요.")
    return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


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
    if SPEED <= 0:
        raise ValueError("SPEED는 0보다 커야 해요.")

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

    whisper = load_whisper() if SUBTITLES else None
    if whisper:
        script.add_track(cc.TrackType.text, "자막")

    all_segments = []  # 모든 영상 조각 (페이드를 붙인 뒤 한꺼번에 타임라인에 넣어요)
    position = 0       # 완성 영상에서 다음 조각이 놓일 위치
    original_total = 0
    subtitle_count = 0
    for i, (start, end) in enumerate(ranges, start=1):
        end = min(end, material.duration)
        original_total += end - start
        print(f"\n[구간 {i}] {format_time(start)} ~ {format_time(end)}")

        if CUT_SILENCE:
            pieces = keep_pieces(start, end, find_silences(video_path, start, end))
            kept = sum(e - s for s, e in pieces)
            print(f"  무음 {format_time(end - start - kept)} 잘라냄 → 조각 {len(pieces)}개")
        else:
            pieces = [(start, end)]
        if not pieces:
            print("  전부 무음이라 건너뛰어요.")
            continue

        placed = []
        segments = []
        for src_start, src_end in pieces:
            segment = cc.VideoSegment(
                material,
                cc.Timerange(position, 0),  # 길이는 속도에 맞춰 자동으로 계산돼요
                source_timerange=cc.Timerange(src_start, src_end - src_start),
                speed=SPEED,
            )
            segments.append(segment)
            placed.append((src_start, src_end, position))
            position += segment.target_timerange.duration

        # 다음 구간으로 넘어갈 때 부드럽게 겹치며 바뀌도록 전환 효과를 넣어요
        # (pyCapCut은 타임라인에 넣기 전에 붙인 전환만 저장해요)
        if TRANSITION and i < len(ranges):
            segments[-1].add_transition(cc.TransitionType.叠化, duration=int(TRANSITION_SEC * SEC))
        all_segments.extend(segments)

        if whisper:
            print("  말을 글자로 바꾸는 중... (구간이 길면 오래 걸려요)")
            last_end = placed[0][2]
            for s, e, text in transcribe(video_path, start, end, whisper):
                ts, te = to_timeline(s, placed, "start"), to_timeline(e, placed, "end")
                if ts is None or te is None:
                    continue
                ts = max(ts, last_end)  # 자막끼리 겹치지 않게
                if te - ts < 0.3 * SEC:
                    continue
                script.add_segment(cc.TextSegment(
                    text, cc.Timerange(ts, te - ts),
                    style=cc.TextStyle(size=SUBTITLE_SIZE, auto_wrapping=True, align=1),
                    border=cc.TextBorder(width=30.0),
                    clip_settings=cc.ClipSettings(transform_y=-0.8),
                ), "자막")
                last_end = te
                subtitle_count += 1
            print(f"  자막 지금까지 {subtitle_count}개")

    if not all_segments:
        raise ValueError("남은 영상이 없어요. 구간이 전부 무음이었어요.")

    # 처음 조각은 서서히 나타나고, 마지막 조각은 서서히 사라지게 해요
    # (조각이 짧으면 페이드도 그 절반 길이로 줄여요)
    if FADE:
        first, last = all_segments[0], all_segments[-1]
        first.add_animation(cc.IntroType.渐显,
                            duration=min(int(FADE_SEC * SEC), first.target_timerange.duration // 2))
        last.add_animation(cc.OutroType.渐隐,
                           duration=min(int(FADE_SEC * SEC), last.target_timerange.duration // 2))

    # pyCapCut은 타임라인에 넣기 전에 붙인 효과만 저장해요
    for segment in all_segments:
        script.add_segment(segment)

    script.save()
    print(f"\n완성! 고른 구간 {format_time(original_total)} → 완성 영상 {format_time(position)}")
    print(f"CapCut을 열고 '{draft_name}' 드래프트를 확인하세요.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[오류] {e}")
        sys.exit(1)
