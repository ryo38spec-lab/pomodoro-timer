#!/usr/bin/env python3
"""ポモドーロタイマー — ターミナルで動くインタラクティブな集中管理ツール"""

import time
import sys
import os
import signal
import subprocess
from datetime import datetime

# ANSI カラーコード
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
WHITE   = "\033[97m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"

WORK_MIN   = 25
SHORT_MIN  = 5
LONG_MIN   = 15
LONG_EVERY = 4  # 4セット目に長い休憩

session_count = 0
total_focus_seconds = 0
start_time = datetime.now()


def clear():
    os.system("clear")


def notify(title: str, message: str):
    """macOS デスクトップ通知"""
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{message}" with title "{title}" sound name "Glass"'],
            capture_output=True,
        )
    except Exception:
        pass


def bar(elapsed: int, total: int, width: int = 40, color: str = GREEN) -> str:
    filled = int(width * elapsed / total)
    empty  = width - filled
    pct    = int(100 * elapsed / total)
    return f"{color}{'█' * filled}{DIM}{'░' * empty}{RESET} {color}{BOLD}{pct:3d}%{RESET}"


def fmt_time(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def fmt_duration(seconds: int) -> str:
    h, rem = divmod(seconds, 3600)
    m, _   = divmod(rem, 60)
    if h > 0:
        return f"{h}時間{m}分"
    return f"{m}分"


def draw(phase: str, elapsed: int, total: int, color: str):
    clear()
    remaining = total - elapsed
    pct = int(100 * elapsed / total)

    # ヘッダー
    print(f"\n  {BOLD}{CYAN}🍅 ポモドーロタイマー{RESET}  {DIM}{start_time.strftime('%H:%M')} 開始{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}\n")

    # フェーズ表示
    phase_label = {
        "work":  f"{RED}{BOLD}  ▶  集中タイム{RESET}",
        "short": f"{GREEN}{BOLD}  ☕  短い休憩{RESET}",
        "long":  f"{MAGENTA}{BOLD}  🌟  長い休憩{RESET}",
    }[phase]
    print(f"  {phase_label}")
    print()

    # タイマー表示
    print(f"  {BOLD}{WHITE}{'  ' + fmt_time(remaining):^20}{RESET}  {DIM}残り{RESET}")
    print()

    # プログレスバー
    print(f"  {bar(elapsed, total, 46, color)}")
    print()

    # セッション情報
    dots = ""
    for i in range(LONG_EVERY):
        if i < (session_count % LONG_EVERY):
            dots += f"{RED}●{RESET} "
        else:
            dots += f"{DIM}○{RESET} "

    print(f"  セッション数: {BOLD}{YELLOW}{session_count}{RESET}  {dots}")
    print(f"  総集中時間:   {BOLD}{CYAN}{fmt_duration(total_focus_seconds + (elapsed if phase == 'work' else 0))}{RESET}")
    print()
    print(f"  {DIM}Ctrl+C でスキップ / 終了{RESET}")


def countdown(phase: str, minutes: int, color: str):
    global total_focus_seconds
    total = minutes * 60
    skip = False

    def handle_skip(sig, frame):
        nonlocal skip
        skip = True

    old = signal.signal(signal.SIGINT, handle_skip)

    for elapsed in range(total + 1):
        draw(phase, elapsed, total, color)
        if skip:
            break
        if elapsed < total:
            time.sleep(1)

    if phase == "work" and not skip:
        total_focus_seconds += total
    elif phase == "work" and skip:
        total_focus_seconds += elapsed

    signal.signal(signal.SIGINT, old)
    return not skip  # True = 完走


def confirm_quit():
    clear()
    print(f"\n  {BOLD}{YELLOW}⚠  本当に終了しますか？{RESET}\n")
    print(f"  {BOLD}総集中時間: {CYAN}{fmt_duration(total_focus_seconds)}{RESET}")
    print(f"  {BOLD}セッション数: {YELLOW}{session_count}{RESET}\n")
    print(f"  {DIM}もう一度 Ctrl+C で終了 / Enter で続行{RESET}\n  ", end="", flush=True)
    try:
        input()
        return False
    except (KeyboardInterrupt, EOFError):
        return True


def main():
    global session_count

    clear()
    print(f"\n  {BOLD}{CYAN}🍅 ポモドーロタイマー{RESET}\n")
    print(f"  {YELLOW}集中{RESET} {WORK_MIN}分  |  {GREEN}短い休憩{RESET} {SHORT_MIN}分  |  {MAGENTA}長い休憩{RESET} {LONG_MIN}分\n")
    print(f"  {DIM}Enter で開始...{RESET}  ", end="", flush=True)
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        print("\n  終了しました。")
        return

    while True:
        # 作業セッション
        session_count += 1
        notify("🍅 集中タイム開始！", f"第 {session_count} セッション — {WORK_MIN}分間集中しましょう")

        completed = countdown("work", WORK_MIN, RED)
        if not completed:
            if confirm_quit():
                break
            session_count -= 1
            continue

        notify("✅ お疲れ様！", "休憩タイムです")

        # 長い休憩 or 短い休憩
        if session_count % LONG_EVERY == 0:
            notify("🌟 長い休憩！", f"{LONG_MIN}分間しっかり休みましょう")
            completed = countdown("long", LONG_MIN, MAGENTA)
        else:
            notify("☕ 短い休憩", f"{SHORT_MIN}分後また頑張りましょう")
            completed = countdown("short", SHORT_MIN, GREEN)

        if not completed:
            if confirm_quit():
                break
            continue

    # 終了サマリー
    clear()
    elapsed_wall = int((datetime.now() - start_time).total_seconds())
    print(f"\n  {BOLD}{CYAN}🍅 お疲れ様でした！{RESET}\n")
    print(f"  ┌{'─' * 36}┐")
    print(f"  │  完了セッション数  {BOLD}{YELLOW}{session_count:>4}{RESET}  回          │")
    print(f"  │  総集中時間        {BOLD}{CYAN}{fmt_duration(total_focus_seconds):>8}{RESET}        │")
    print(f"  │  経過時間          {DIM}{fmt_duration(elapsed_wall):>8}{RESET}        │")
    print(f"  └{'─' * 36}┘\n")


if __name__ == "__main__":
    main()
