import subprocess
import os

font_bold = "C\\:/Windows/Fonts/arialbd.ttf"
font_regular = "C\\:/Windows/Fonts/arial.ttf"

def escape_ffmpeg_text(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

def gen_title_card():
    # Title card: 1920x1080
    vf_filters = [
        "color=c=0x0b0f19:s=1920x1080:d=1",
        "drawbox=x=0:y=0:w=1920:h=8:color=0x00f2fe@1:t=fill",
        "drawbox=x=160:y=160:w=1600:h=760:color=0x111827@0.95:t=fill",
        "drawbox=x=160:y=160:w=1600:h=760:color=0x1f2937@1:t=2",
        f"drawtext=fontfile='{font_bold}':text='AIRLOCK':fontsize=88:fontcolor=0xffffff:x=(w-text_w)/2:y=220",
        f"drawtext=fontfile='{font_bold}':text='{escape_ffmpeg_text('DETERMINISTIC CI GUARDRAILS FOR AI CODING AGENTS')}':fontsize=28:fontcolor=0x00e5ff:x=(w-text_w)/2:y=340",
        f"drawtext=fontfile='{font_regular}':text='{escape_ffmpeg_text('Supervised Autonomy for GitLab Duo Agent Platform')}':fontsize=26:fontcolor=0x94a3b8:x=(w-text_w)/2:y=400",
        "drawbox=x=560:y=470:w=800:h=2:color=0x374151:t=fill",
        f"drawtext=fontfile='{font_bold}':text='{escape_ffmpeg_text('GitLab Transcend Hackathon — Path A (Start Fresh)')}':fontsize=24:fontcolor=0xfbbf24:x=(w-text_w)/2:y=510",
        f"drawtext=fontfile='{font_regular}':text='{escape_ffmpeg_text('Autonomous agents that can ship, but cannot break the rules.')}':fontsize=24:fontcolor=0xe5e7eb:x=(w-text_w)/2:y=570",
        f"drawtext=fontfile='{font_regular}':text='{escape_ffmpeg_text('Dual-Agent Split • Verify-Twice SAST • Policy Gate • Signed Scorecards')}':fontsize=22:fontcolor=0x38bdf8:x=(w-text_w)/2:y=630",
        "drawbox=x=560:y=700:w=800:h=1:color=0x374151:t=fill",
        f"drawtext=fontfile='{font_bold}':text='{escape_ffmpeg_text('Live Production: https://airlock-guardrails.vercel.app')}':fontsize=22:fontcolor=0x10b981:x=(w-text_w)/2:y=740",
        f"drawtext=fontfile='{font_regular}':text='{escape_ffmpeg_text('Creator: Vikas Sharma • GitLab: @beyondnothing • Supervised Autonomy')}':fontsize=20:fontcolor=0x6b7280:x=(w-text_w)/2:y=800",
    ]
    vf = ",".join(vf_filters)
    cmd = [
        "ffmpeg", "-f", "lavfi", "-i", vf,
        "-frames:v", "1", "-y", "video_assets/00_title_card.png"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("Title card error:", res.stderr)
    else:
        print("Generated video_assets/00_title_card.png")

def gen_end_card():
    # End card: 1920x1080
    vf_filters = [
        "color=c=0x0b0f19:s=1920x1080:d=1",
        "drawbox=x=0:y=1072:w=1920:h=8:color=0x10b981@1:t=fill",
        "drawbox=x=160:y=160:w=1600:h=760:color=0x111827@0.95:t=fill",
        "drawbox=x=160:y=160:w=1600:h=760:color=0x1f2937@1:t=2",
        f"drawtext=fontfile='{font_bold}':text='AIRLOCK':fontsize=84:fontcolor=0xffffff:x=(w-text_w)/2:y=220",
        f"drawtext=fontfile='{font_bold}':text='{escape_ffmpeg_text('SAFE AGENTS • VERIFIED FIXES • HUMANS IN CONTROL')}':fontsize=28:fontcolor=0x10b981:x=(w-text_w)/2:y=330",
        "drawbox=x=560:y=400:w=800:h=2:color=0x374151:t=fill",
        f"drawtext=fontfile='{font_bold}':text='{escape_ffmpeg_text('Live Interactive Showcase:')}':fontsize=24:fontcolor=0x94a3b8:x=400:y=450",
        f"drawtext=fontfile='{font_regular}':text='{escape_ffmpeg_text('https://airlock-guardrails.vercel.app')}':fontsize=24:fontcolor=0x00e5ff:x=760:y=450",
        f"drawtext=fontfile='{font_bold}':text='{escape_ffmpeg_text('GitLab Repository:')}':fontsize=24:fontcolor=0x94a3b8:x=400:y=510",
        f"drawtext=fontfile='{font_regular}':text='{escape_ffmpeg_text('gitlab.com/beyondnothing-group/beyondnothing-project')}':fontsize=24:fontcolor=0x38bdf8:x=760:y=510",
        f"drawtext=fontfile='{font_bold}':text='{escape_ffmpeg_text('GitHub Mirror:')}':fontsize=24:fontcolor=0x94a3b8:x=400:y=570",
        f"drawtext=fontfile='{font_regular}':text='{escape_ffmpeg_text('github.com/vikassharma270907-alt/airlock-guardrails')}':fontsize=24:fontcolor=0x38bdf8:x=760:y=570",
        f"drawtext=fontfile='{font_bold}':text='{escape_ffmpeg_text('Hackathon Showcase:')}':fontsize=24:fontcolor=0x94a3b8:x=400:y=630",
        f"drawtext=fontfile='{font_regular}':text='{escape_ffmpeg_text('gitlab.com/gitlab-ai-hackathon/transcend-october-2026/43727879/showcase')}':fontsize=22:fontcolor=0xe5e7eb:x=760:y=630",
        "drawbox=x=560:y=700:w=800:h=1:color=0x374151:t=fill",
        f"drawtext=fontfile='{font_regular}':text='{escape_ffmpeg_text('GitLab Transcend Hackathon 2026 • Path A: Supervised Autonomy • MIT License')}':fontsize=22:fontcolor=0xfbbf24:x=(w-text_w)/2:y=740",
        f"drawtext=fontfile='{font_regular}':text='{escape_ffmpeg_text('Created by Vikas Sharma (@beyondnothing / beyondnothing01@gmail.com)')}':fontsize=20:fontcolor=0x6b7280:x=(w-text_w)/2:y=800",
    ]
    vf = ",".join(vf_filters)
    cmd = [
        "ffmpeg", "-f", "lavfi", "-i", vf,
        "-frames:v", "1", "-y", "video_assets/99_end_card.png"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("End card error:", res.stderr)
    else:
        print("Generated video_assets/99_end_card.png")

if __name__ == "__main__":
    gen_title_card()
    gen_end_card()
