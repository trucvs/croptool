# Video Crop Studio

Cong cu Python co giao dien do hoa de crop spatial dimensions cho video bang `ffmpeg`, phu hop de mo va chay truc tiep trong Visual Studio Code.

## Tinh nang

- Chon video input va output bang giao dien.
- Doc metadata video truc tiep tu `ffmpeg`.
- Nhap toa do crop theo `x`, `y`, `width`, `height`.
- Co nut `Full Frame`, `Center Crop` va preset ratio (`1:1`, `4:3`, `16:9`, `9:16`, `21:9`).
- Preview frame dau voi khung overlay de xem vung crop.
- Xuat video da crop bang `ffmpeg`, hien thi tien trinh va log trong UI.
- Su dung `dearpygui` cho desktop UI va `imageio-ffmpeg` de co san binary FFmpeg.

## Yeu cau

- Python 3.9+
- Cac package trong `requirements.txt`

### Cai dependencies

Mo Terminal trong thu muc project va chay:

```bash
python3 -m pip install --user -r requirements.txt
```

Neu ban muon dung virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Chay trong VS Code

1. Mo thu muc project trong VS Code.
2. Mo Terminal va chay:

```bash
python3 video_crop_tool.py
```

Hoac dung profile chay san co trong `.vscode/launch.json`.

## Cach dung

1. Bam `Chon video` de tai file input.
2. Chinh `x`, `y`, `width`, `height` theo vung muon crop.
3. Co the bam `Ap dung preset`, `Center Crop`, hoac `Full Frame`.
4. Kiem tra vung crop tren khung preview.
5. Bam `Crop va xuat video` de tao file output.

## Ghi chu ky thuat

- Video duoc encode lai bang `libx264`.
- Audio duoc encode sang `AAC` de output `.mp4` hoat dong on dinh hon.
- App uu tien dung binary FFmpeg duoc cung cap boi `imageio-ffmpeg`, nen khong can cai `ffmpeg` hoac `ffprobe` he thong.
