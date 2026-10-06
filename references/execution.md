# 安裝與自動剪輯

本套件由 AI 助手讀素材、選材及填計劃，附帶程式執行轉錄、同步分析、HTML 動態、混音與輸出。需要可讀本機檔案、執行命令的 AI 工具，例如 Codex；純 terminal 執行者需自行提供剪輯計劃。沒有附另一個 LLM，也不用其他剪輯 Skills 或 API key。

## 安裝

下載整個資料夾，放入工具的 Skills 目錄。只下載 `SKILL.md` 不會取得執行程式。在 Codex 可使用 `~/.codex/skills/dotai-testimonial-reels/`；已有同名版本先比較並備份。

需要 Python 3.9–3.12、網絡及足夠磁碟空間。首次安裝在 `.runtime/` 建隔離環境，下載 Python 依賴、Chromium headless、FFmpeg binary 和繁體中文字體；不改其他 Skills。依賴預留約 2GB，轉錄模型及素材／輸出另計。Linux 可能還需要 Chromium 系統依賴；本版實測 macOS，Windows／Linux 未驗收。

```sh
python3 scripts/run.py doctor
```

`run.py` 首次使用會自動執行 `bootstrap.py`，後續沿用環境。語音模型在首次轉錄才下載；原音訊本機處理。已有字幕可手動用 `python3 scripts/bootstrap.py --no-asr` 安裝較少依賴。

底層方法：[Playwright 安裝](https://playwright.dev/python/docs/library)、[headless browser](https://playwright.dev/python/docs/browsers)、[faster-whisper](https://github.com/SYSTRAN/faster-whisper)、[FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html)。下載及執行各依賴使用其自身授權；字體來源與聲音方法見 [third-party.md](third-party.md)。

## 分析素材

```sh
python3 scripts/run.py prepare --source /path/voice-or-camera.mp4 \
  --speaker /path/camera.mp4 --screen /path/screen.mp4 \
  --transcript /path/transcript.srt --output /path/edit-project
```

- `--source` 是原聲／逐字稿時間的主來源，可是影片或音訊。
- `--speaker` 是真人影片；未提供時使用含畫面的主來源。
- `--screen` 可省略，此時製作全真人版。
- `--transcript` 接受 SRT、VTT 或 `{start,end,text}` JSON；省略才執行本機 ASR。
- `--model small` 預設兼顧 CPU 使用量，`tiny` 只適合快速測試。廣東話品質可改 `--model large-v3-turbo --language yue`，模型較大、CPU 較慢；不保證原話準確，仍須聽校。其他語言用 `--language auto`。
- 輸出 `transcript.json/.srt/.md`、素材資訊、contact 圖及待 AI 選材的 `job.json`。

準備圖片只用來找片段；正式影片仍播放原片。選材時可用 `python3 scripts/run.py frames --source /path/source.mp4 --times 12 30 45 --output /path/source-frames` 查看具體步驟，必要時加 `--crop x y width height`。多人影片先核姓名與說話者，不用臉部相似度冒認。錄屏與真人在同一檔時，可在兩個 source 欄位各設 crop。多段相機素材可各放入 `sources.camera01`／`camera02`，每段指定 `speaker_source`；錄屏同樣可用 `screen_source`。AI逐檔核偏移及crop，不要求先合成一條長片。

## 同步與裁切

```sh
python3 scripts/run.py sync --master /path/master.mp4 \
  --secondary /path/screen-with-audio.mp4 --output /path/sync.json
```

以共同音訊求一個固定偏移，低信心或重複模式會拒絕。核對前後共同事件再套用；無共同音訊、跨時鐘漂移或分段錄影，由 AI 用可觀察事件記錄各段映射。

**偏移定義：副素材時間 = 主素材時間 + offset。** 正值代表副素材對應時間較大。可在 `sources.screen.offset` 填一次，或每段用 `screen_start`／`speaker_start` 覆寫。對位超出原片會報錯，不靜默補成不相關畫面。

Crop 是 `[x,y,width,height]`，使用來源像素；不是最終畫布座標。先看素材資訊及代表畫面再填。

## AI 選材與計劃

AI 讀逐字稿及 contact 圖，選完整句子，寫入 `job.json`；依原聲配 Hook、作品、工作轉變、流程及 CTA。用 [job-template.json](../assets/job-template.json) 參照欄位。不要只選頭 90 秒或靠關鍵字代替故事判斷。

- `start/end`：原聲主來源秒數；每段可跳到不同時間。
- `layout`：`speaker` 全真人 Hook，或 `split` 作品上／真人下。
- `title`：編輯標題；`step` 對應 `steps` 的 0-based index；流程最多 7 格，每格用約 4–8 字短標籤。
- `callouts`：`at/duration` 用該段**剪後秒數**；左右圖示及短字只在相關時刻出現。
- `stats`：已核原聲數字；`time_fraction` 用方塊收縮，`multiple` 用計數動畫。沒有原句就不用數字。
- `speed`：.5–2，全片一次換算；字幕及原聲同步。已加速素材用 1.0。
- `max_seconds`：片長硬上限；超長需重新選材，不自動截斷末句。
- `geometry` 或 `layout_preset`：控制兩個畫面、字幕與標題位置。預設是 1080×1920；作品 `screen_fit` 可設 `contain`（完整展示）或 `cover`（裁邊填滿）。
- 字幕來源可保持原句，在句段合理邊界拆成可讀短行；ASR 的詞時間是草稿，不當精確核實。

## 品牌、聲音與輸出

`logo/header_photo/footer_photo` 填使用者自己的素材。未有 Logo 時只用品牌文字，不仿製官方圖形。`[[重點字]]` 可用於編輯標題／CTA 的藍色重點。

預設產生柔和合成底樂、開場 Hit、工具滑入 Whoosh 和數字 Counter，按原聲壓低附加聲音。沒有外部樣本。提供 `music`／`sfx` 時使用指定素材；`auto_music:false`、`auto_sfx:false` 可關閉自動聲音。每個 SFX 用 `path/at/trim/duration/gain`，`at` 是全片剪後時間。

```sh
python3 scripts/run.py validate --job /path/edit-project/job.json
python3 scripts/run.py render --job /path/edit-project/job.json \
  --output /path/version-01 --keep-pairs
```

AI 在使用者已要求製片時直接完成本機預覽，不要求使用者手填 JSON。若只要求文字稿，就停在稿件交付。輸出已有成片時要另開版本目錄；只有明確要覆寫才用 `--overwrite`。

輸出包括 `final.mp4`、完整 SRT、逐句文字、切點、HTML、播放頁、驗證收據及同編號 A真人有聲／B螢幕無聲。`rebuild/job.json` 使用相對路徑精選素材，可移動後再剪；素材已 crop／加速，重做 speed=1.0。未選原長片不包含在重做包。

```sh
python3 scripts/run.py render --job /moved/rebuild/job.json \
  --output /new/version-02 --keep-pairs
```

HTML 使用確定時間 seek，每一影格從本機 Chromium 合成，再由 FFmpeg 編碼；不是只輸出網頁預覽。渲染期間顯示進度；完整 90 秒的時間依機器而異，不保證即時輸出。保留 partial／原版本，不刪使用者素材。

## 自己試一次

```sh
python3 scripts/run.py demo --output /path/fictional-demo
```

生成 6 秒測試片、字幕、不同工具圖示及混音。全部測試內容標示示例，沒有真人好評。測試與格式成功不代表 ASR、來源權限或某個新個案已驗收。
