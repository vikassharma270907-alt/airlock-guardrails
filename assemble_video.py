import os
import sys
import subprocess
import time

FONT_BOLD = "C\\:/Windows/Fonts/arialbd.ttf"
FONT_REGULAR = "C\\:/Windows/Fonts/arial.ttf"
WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(WORKSPACE_DIR, "video_assets")
SEGMENTS_DIR = os.path.join(WORKSPACE_DIR, "video_segments")
OUTPUT_VIDEO = os.path.join(WORKSPACE_DIR, "airlock_demo_showcase.mp4")
SRT_PATH = os.path.join(WORKSPACE_DIR, "docs", "airlock_demo.srt")

os.makedirs(SEGMENTS_DIR, exist_ok=True)

def escape_text(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

# Segment definitions: (name, image_file, duration, is_card, title, subtitle)
SEGMENTS = [
    # 0:00 -> 0:04 (4.0s) Title Card
    ("seg_01_title", "00_title_card.png", 4.0, True, "", ""),
    
    # 0:04 -> 0:11 (7.0s) Hero
    ("seg_02_hero", "hero_top.png", 7.0, False, "AIRLOCK OVERVIEW", "Supervised Autonomy for GitLab Duo • Deterministic CI Guardrails"),
    
    # 0:11 -> 0:18.5 (7.5s) Architecture Diagram
    ("seg_03_arch", "arch_diagram.png", 7.5, False, "ARCHITECTURE: CONTROL VS DATA PLANE", "Dual-Agent Split • Deterministic CI Guardrails"),
    
    # 0:18.5 -> 0:35.0 (16.5s) Gate 1 - Prompt Injection
    ("seg_04_triage_exploit", "02_dual_agent_triage.png", 16.5, False, "GATE 1: DUAL-AGENT TRIAGE", "Untrusted Issue Input • Instruction Override in HTML Comment"),
    
    # 0:35.0 -> 0:52.0 (17.0s) Gate 1 - Sanitized Output & Reader/Writer Split
    ("seg_05_triage_blocked", "02_dual_agent_triage.png", 17.0, False, "GATE 1: DUAL-AGENT TRIAGE", "Reader Rigid JSON • Writer Posts Sanitized Warning (INJECTION BLOCKED)"),
    
    # 0:52.0 -> 1:08.0 (16.0s) Gate 2 - Insecure eval() Blocked
    ("seg_06_sast_blocked", "03_sast_gate_blocked.png", 16.0, False, "GATE 2: VERIFY-TWICE SAST GATE", "MR !4: Unit Tests Pass, but SAST Gate Blocks Insecure eval()"),
    
    # 1:08.0 -> 1:23.8 (15.8s) Gate 2 - Remediated Fix & Re-scan Zero Findings
    ("seg_07_sast_passed", "03b_jobs_status.png", 15.8, False, "GATE 2: VERIFY-TWICE SAST GATE", "Remediated Safely • Re-scan Confirms Zero Findings & Gate Passes"),
    
    # 1:23.8 -> 1:36.0 (12.2s) Gate 3 - CI Tampering Blocked
    ("seg_08_policy_ci", "04_policy_gate_diff.png", 12.2, False, "GATE 3: POLICY GATE & CONTROL PLANE", "MR !2: .gitlab-ci.yml Tampering Halted with Exit Code 1"),
    
    # 1:36.0 -> 1:47.8 (11.8s) Gate 3 - Test Rename Evasion Defense
    ("seg_09_policy_evasion", "04b_pipelines_list.png", 11.8, False, "GATE 3: POLICY GATE & TEST DEFENSE", "MR !3: git diff --no-renames Catches Test Rename/Deletion Evasion"),
    
    # 1:47.8 -> 2:08.0 (20.2s) Main Pipeline #2993995494
    ("seg_10_main_pipeline", "05_pipeline_success.png", 20.2, False, "PIPELINE #2993995494 (MAIN BRANCH)", "9 DevSecOps Stages • 53 Tests Passed • Staging Publish • Scorecard"),
    
    # 2:08.0 -> 2:24.5 (16.5s) Supervised Release Gate
    ("seg_11_manual_gate", "06_manual_prod_gate.png", 16.5, False, "SUPERVISED PRODUCTION RELEASE GATE", "Production Release Locked • Manual Maintainer Action Required"),
    
    # 2:24.5 -> 2:42.0 (17.5s) End Card & Links
    ("seg_12_end_card", "99_end_card.png", 17.5, True, "", ""),
]

def build_segment(name, img_file, duration, is_card, title, subtitle):
    img_path = os.path.join(ASSETS_DIR, img_file)
    out_path = os.path.join(SEGMENTS_DIR, f"{name}.mp4")
    
    if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        print(f"Segment {name} already exists, skipping render.")
        return out_path
    
    if not os.path.exists(img_path):
        raise FileNotFoundError(f"Missing asset image: {img_path}")
    
    right_tag = "airlock-guardrails.vercel.app"
    
    if is_card:
        # Full-screen 1920x1080 card without banner
        vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0b0f19"
    else:
        # 1920x1080 with branded top banner bar
        vf_parts = [
            "scale=1920:1020:force_original_aspect_ratio=decrease",
            "pad=1920:1020:(ow-iw)/2:(oh-ih)/2:color=0x0b0f19",
            "pad=1920:1080:0:60:color=0x0b0f19",
            "drawbox=x=0:y=0:w=1920:h=60:color=0x0f172a@1:t=fill",
            "drawbox=x=0:y=58:w=1920:h=2:color=0x00e5ff@1:t=fill",
            f"drawtext=fontfile='{FONT_BOLD}':text='AIRLOCK':fontsize=24:fontcolor=0xffffff:x=30:y=18",
            "drawbox=x=150:y=18:w=2:h=24:color=0x334155@1:t=fill",
            f"drawtext=fontfile='{FONT_BOLD}':text='{escape_text(title)}':fontsize=20:fontcolor=0x00e5ff:x=170:y=20",
            f"drawtext=fontfile='{FONT_REGULAR}':text='{escape_text('— ' + subtitle)}':fontsize=17:fontcolor=0x94a3b8:x=560:y=22",
            f"drawtext=fontfile='{FONT_REGULAR}':text='{escape_text(right_tag)}':fontsize=18:fontcolor=0x64748b:x=w-text_w-30:y=22",
        ]
        vf = ",".join(vf_parts)
    
    cmd = [
        "ffmpeg", "-loop", "1", "-i", img_path,
        "-vf", vf,
        "-t", str(duration), "-r", "30",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-y", out_path
    ]
    
    print(f"Rendering {name} ({duration}s)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error rendering {name}: {res.stderr}")
        sys.exit(1)
    return out_path

def main():
    start_time = time.time()
    total_duration = sum(s[2] for s in SEGMENTS)
    print(f"=== Assembling Airlock Demo Video ({total_duration}s / 2m 42s) ===")
    
    segment_files = []
    for name, img_file, duration, is_card, title, subtitle in SEGMENTS:
        seg_path = build_segment(name, img_file, duration, is_card, title, subtitle)
        segment_files.append(seg_path)
    
    # Write concat demuxer list
    concat_list_path = os.path.join(SEGMENTS_DIR, "concat_list.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in segment_files:
            # ffmpeg concat demuxer needs forward slashes or escaped backslashes
            clean_p = p.replace("\\", "/")
            f.write(f"file '{clean_p}'\n")
    
    raw_concat_video = os.path.join(SEGMENTS_DIR, "raw_concat.mp4")
    print("\nConcatenating segments...")
    concat_cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-c", "copy",
        "-y", raw_concat_video
    ]
    res = subprocess.run(concat_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error concatenating: {res.stderr}")
        sys.exit(1)
    
    # Burn subtitles and add silent audio track
    print("\nBurning subtitles from docs/airlock_demo.srt & generating final master MP4...")
    sub_filter = "subtitles=docs/airlock_demo.srt:force_style='Fontname=Arial,Fontsize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,MarginV=35'"
    
    final_cmd = [
        "ffmpeg",
        "-i", raw_concat_video,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-vf", sub_filter,
        "-t", str(total_duration),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-y", OUTPUT_VIDEO
    ]
    res = subprocess.run(final_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error producing final video: {res.stderr}")
        sys.exit(1)
    
    elapsed = time.time() - start_time
    file_size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
    print(f"\nSUCCESS!")
    print(f"Output Video: {OUTPUT_VIDEO}")
    print(f"File Size: {file_size_mb:.2f} MB")
    print(f"Total Duration: {total_duration:.1f}s (2:42)")
    print(f"Elapsed Generation Time: {elapsed:.1f}s")

if __name__ == "__main__":
    main()
