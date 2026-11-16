"""Create an original, silent local rehearsal clip and cover for upload preview."""

from pathlib import Path
import subprocess

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "pilot-video"
FONT = "C:/Windows/Fonts/msyh.ttc"
BOLD = "C:/Windows/Fonts/msyhbd.ttc"


def frame(index: int, title: str, subtitle: str) -> Path:
    width, height = 1280, 720
    im = Image.new("RGB", (width, height))
    pixels = im.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = (9 + y // 75, 24 + x // 120, 55 + y // 60)
    draw = ImageDraw.Draw(im)
    draw.ellipse((960, -180, 1430, 290), fill=(22, 93, 143))
    draw.ellipse((-200, 500, 340, 1000), fill=(13, 71, 114))
    draw.rounded_rectangle((68, 72, 320, 130), 18, fill=(42, 135, 199))
    draw.text((92, 82), "小白 · 本地试播", font=ImageFont.truetype(BOLD, 27), fill="white")
    draw.text((72, 248), title, font=ImageFont.truetype(BOLD, 65), fill="white")
    draw.text((76, 365), subtitle, font=ImageFont.truetype(FONT, 32), fill=(183, 225, 248))
    draw.text((76, 641), f"本地彩排  ·  {index + 1}/3  ·  AI 生成画面", font=ImageFont.truetype(FONT, 23), fill=(150, 187, 209))
    path = OUT / f"frame{index:02}.png"
    im.save(path)
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frame(0, "你好，我是小白", "一个正在学习做视频和直播的 AI 主播")
    frame(1, "先学会观察", "今天已经在 B 站完成了一次只读浏览")
    frame(2, "从本地试播开始", "评论、投稿和开播都先经过预览与验收")
    Image.open(OUT / "frame00.png").save(OUT / "cover.jpg", quality=93)
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", "1/4", "-i", str(OUT / "frame%02d.png"),
        "-t", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "25",
        str(OUT / "小白-local-pilot.mp4"),
    ]
    subprocess.run(command, check=True)
    print(OUT / "小白-local-pilot.mp4")


if __name__ == "__main__":
    main()
