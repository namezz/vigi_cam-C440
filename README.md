# VIGI 攝影機控制專案

<!--
專案說明：
本專案為一個用於控制 TP-Link VIGI 攝影機的 Python 專案，提供警報管理、音訊處理和串流功能。

備註：
- 請確保已安裝 ffmpeg 以支援音訊檔案轉換，安裝教學可參考：https://vocus.cc/article/64701a2cfd897800014daed0
- 作業系統為 Windows 時，請使用 requirements.txt 進行套件安裝。
-->
這是一個用於控制 TP-Link VIGI 攝影機的 Python 專案，提供警報管理、音訊處理和串流功能。

## 專案結構

```
├── vigi_cam(C440)/          # 主要攝影機控制模組
│   ├── demo_alarm.py        # 警報功能演示
│   ├── demo_audio_manage.py # 音訊管理演示
│   └── func/               # 核心功能模組
│       ├── vigiapi4cam.py  # VIGI API 控制類別
│       ├── cam_stream.py   # 攝影機串流模組
│       └── audio2vigiFormat.py # 音訊格式轉換
├── sound_api/              # 音訊 API 相關工具
├── audio/                  # 音訊檔案
└── output.g711            # G.711 格式音訊輸出
```

## 主要功能

### 1. 攝影機控制
- 身份驗證與連線管理
- 手動觸發聲光警報
- 音量控制（1-100）
- 警報聲音類型設定

### 2. 音訊管理
- 自訂音檔上傳（G.711 格式）
- 音檔重新命名
- 音檔刪除
- 支援中文警報聲音

### 3. 串流功能
- 即時攝影機畫面串流
- RTSP 串流支援
- 同時警報和串流

### 4. ONVIF 控制
- 音頻異常偵測
- 聲光警報聯動
- 設備資訊探索

## 快速開始

### 設定攝影機資訊
在 [`vigiapi4cam.py`](vigi_cam(C440)/func/vigiapi4cam.py) 中修改：
```python
IP_ADDRESS = '192.168.0.60'  # 您的攝影機 IP
USERNAME = 'admin'           # 使用者名稱
PASSWORD = '123456'          # 密碼
```

### 基本使用範例

#### 1. 觸發警報
```bash
python demo_alarm.py
```
選擇功能：
- 觸發手動聲光警報
- 測試喇叭聲音
- 開啟攝影機串流
- 同時觸發警報和串流

#### 2. 管理音訊檔案
```bash
python demo_audio_manage.py
```
功能包括：
- 同步自訂音檔到攝影機
- 刪除指定音檔
- 重新命名音檔

## API 使用說明

### 初始化攝影機連線
```python
from func.vigiapi4cam import VigiApi

vigi_cam = VigiApi(IP_ADDRESS, USERNAME, PASSWORD)
if vigi_cam.authenticate():
    print("連線成功")
```

### 觸發警報
```python
# 開始警報 (聲音ID=1, 音量=10)
vigi_cam.trigger_manual_alarm(action="start", sound_id=1, volume=10)

# 停止警報
vigi_cam.trigger_manual_alarm(action="stop")
```

### 管理自訂音檔
```python
# 獲取音檔列表
audio_list = vigi_cam.get_custom_audio_list()

# 上傳音檔到指定槽位
audio_files = ["path/to/audio1.g711", "path/to/audio2.g711"]
vigi_cam.sync_custom_audios(audio_files)

# 重新命名音檔
vigi_cam.rename_custom_audio(sound_id=101, new_name="新警報聲音")
```

### 攝影機串流
```python
# 建立串流物件
camera_stream = vigi_cam.create_camera_stream()

# 顯示即時畫面
camera_stream.show_live_stream('VIGI Camera Live Stream')
```

## 音訊格式支援

- **輸入格式**: WAV, MP3
- **輸出格式**: G.711 (A-law/μ-law)
- **轉換工具**: [`audio2vigiFormat.py`](vigi_cam(C440)/func/audio2vigiFormat.py)

## 檔案說明

| 檔案 | 功能 |
|------|------|
| [`vigiapi4cam.py`](vigi_cam(C440)/func/vigiapi4cam.py) | 核心 API 控制類別 |
| [`cam_stream.py`](vigi_cam(C440)/func/cam_stream.py) | 攝影機串流功能 |
| [`discover_devinfo.py`](sound_api/discover_devinfo.py) | ONVIF 設備控制 |
| [`demo_alarm.py`](vigi_cam(C440)/demo_alarm.py) | 警報功能演示腳本 |
| [`demo_audio_manage.py`](vigi_cam(C440)/demo_audio_manage.py) | 音訊管理演示腳本 |

## 注意事項

1. **網路連線**: 確保攝影機與電腦在同一網段
2. **音訊格式**: 自訂音檔需轉換為 G.711 格式
3. **槽位限制**: 自訂音檔槽位為 101, 102, 103
4. **音量範圍**: 1-100（建議使用 1-30）

## 相依套件

- `urllib3` - HTTP 請求
- `cryptography` - 加密功能
- `opencv-python` - 視訊處理
- `onvif-zeep` - ONVIF 協定支援

## 授權

此專案用於 TP-Link VIGI 攝影機控制，請遵守相關使用條款。

---

> 本說明文件由 AI 協助生成，內容僅供參考，請依實際需求調整與驗證。
