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
- Co san cau hinh dong goi Windows bang `PyInstaller`.

## Yeu cau

- Python voi binary wheel tuong thich cho `dearpygui==2.2`
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

Tren Windows PowerShell, co the dung:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Chay trong VS Code

1. Mo thu muc project trong VS Code.
2. Mo Terminal va chay:

```bash
python3 video_crop_tool.py
```

Hoac dung profile chay san co trong `.vscode/launch.json`.

## Dong Goi Windows

Project da co san:

- `packaging/video_crop_tool.spec` cho `PyInstaller`
- `packaging/build_windows.ps1` de build ban Windows
- `packaging/build_vdi_bundle.ps1` de tao source bundle `.zip` cho VDI
- `.github/workflows/windows-release.yml` de build artifact/release tren GitHub Actions

### Build tren may Windows

Mo PowerShell trong thu muc project va chay:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\packaging\build_windows.ps1 -Version v0.1.0
```

File zip release se duoc tao tai:

```text
release\VideoCropStudio-v0.1.0-windows-x64.zip
```

### Tao source bundle cho VDI

Neu ban muon mang source bundle sang Windows VDI va chay bang Python:

```powershell
.\packaging\build_vdi_bundle.ps1
```

File zip se duoc tao tai:

```text
packaging\VideoCropStudio-source-vdi-py313.zip
```

### Build release tu GitHub

- Push mot tag theo dang `v*`, vi du `v0.1.0`
- Workflow `Windows Release` se build file `.exe`, dong goi thanh `.zip` va attach vao GitHub Release
- Neu chi muon test build ma khong tao release, co the chay workflow bang `workflow_dispatch`

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
- Logic da duoc tach thanh package `croptool/` de de test va bao tri, trong khi `video_crop_tool.py` van duoc giu lam entrypoint.
- Windows release duoc dong goi theo kieu one-folder, vi vay can giu nguyen cac file nam cung `VideoCropStudio.exe` sau khi giai nen.
