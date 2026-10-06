# 由散亂影片素材到客戶好評 Skill

把一堆訪問、課堂錄影、Zoom 錄屏及作品素材，整理成一條有真實說話、有成果證明、有工作轉變的客戶好評 Reels。AI 助手負責找素材、選句及組故事，附帶程式負責實際剪片。

**散亂素材 → 素材清單 → 逐字稿與金句 → 真人／作品配對 → 故事初剪 → 字幕、動畫與聲音 → 成片及重做包。**

下載完整套件，提供素材資料夾，由 AI 助手整理及輸出 1080×1920 MP4；使用者不用手填切點或安裝其他公司 Skills。

需要具備本機檔案與命令工具的 AI 助手，例如 Codex。AI 助手負責語意選材，附帶程式負責轉錄及實際製片；不是另一個自帶 LLM 的獨立應用程式。

## 安裝後直接講

> 用 $dotai-testimonial-reels。素材資料夾係＿＿，今次客戶係＿＿。幫我整理散亂影片、找真實金句及作品畫面，剪一條 90 秒內嘅客戶好評 Reels。用深藍上下雙畫面、完整字幕、HTML 動畫同音效，交初剪、逐句稿、配對素材同重做包。

下載**全部資料夾**，不是只下載一份 Markdown。在 Codex 可放入 `~/.codex/skills/dotai-testimonial-reels/`。第一次執行自動建立 `.runtime/`、安裝依賴及繁體字體；原素材在本機處理，不用 API key。需要 Python 3.9–3.12 及網絡，安裝與模型佔用另見 [執行說明](references/execution.md)。

## 由散亂素材到好評成片

| 階段 | AI 助手與程式做甚麼 | 你收到甚麼 |
| --- | --- | --- |
| 整理素材 | 找原聲、真人、錄屏、作品及已有字幕，標示重複和缺漏 | 素材清單與角色分類 |
| 找真實金句 | 讀逐字稿、聽上下文，找 Before／After 及具體成果 | 原句、來源檔與時間碼 |
| 配對畫面 | 核同步，將每句說話配到相關作品；多相機逐段選 | 同編號、同長度 A真人／B作品素材 |
| 串成故事 | 金句開場、客戶身份、作品、工作轉變、流程及 CTA | 逐句故事、畫面配搭與初剪 |
| 做後期 | 實際影片、完整字幕、HTML 動態、底樂及音效 | 90 秒內直式 MP4 與播放頁 |
| 保存重做 | 記來源、切點、設定及精選媒體 | SRT、文字稿、配對素材、重做包 |

素材整理與故事選材由 AI 助手執行，不是只靠檔名或固定關鍵字。來源未證明的身份、金句與成效不會補寫；自動剪出初稿後，字幕和故事仍需看片驗收。

## 已附哪些程式

| 程式 | 實際功能 |
| --- | --- |
| `scripts/run.py`／`bootstrap.py` | 自動安裝、環境檢查與統一入口 |
| `scripts/reels.py prepare` | 本機 ASR 或讀已有字幕、來源資訊與 contact 圖 |
| `scripts/reels.py sync` | 共同音訊固定偏移候選、低信心拒絕 |
| `scripts/reels.py render` | 真實上下畫面、SRT、HTML逐影格動態、混音與 MP4 |
| `scripts/sound.py` | 程序合成輕底樂、Hit、Whoosh、Counter |
| `scripts/demo.py` | 不含真人資料的 6 秒端到端示例 |

## 成片風格與交付

真實原聲 Hook → 可見 Before／After → 工作轉變 → 流程 → CTA。深藍底、作品上／真人下、中間完整字幕、短工具圖示左右滑入、少量藍色重點。數字有原句才做動畫；人物、成效及作品不從另一個個案照搬。

輸出 MP4、SRT、逐句故事、source/cut 對照、播放頁、驗證收據；加 `--keep-pairs` 同時保存同編號同長度 A真人有聲／B螢幕無聲及可移動的精選重做包。Logo／照片可用自己的素材，未提供便用簡單品牌文字。

## 先自己試一次

```sh
python3 scripts/run.py doctor
python3 scripts/run.py demo --output /path/fictional-demo
```

[完整 Skill](SKILL.md) · [安裝、命令與欄位](references/execution.md) · [故事及剪輯計劃](assets/case-plan.md) · [job 模板](assets/job-template.json) · [版面示例](examples/layout-preset.json) · [視覺與驗收](references/customer-testimonial-workflow.md) · [依賴與素材](references/third-party.md)

目前實測 macOS、短片、字幕讀取、本機短音訊 ASR、固定偏移、HTML 動態、混音及精選包重做。ASR 仍需聽校；完整一小時素材、Windows／Linux 與新使用者試用未驗收。品牌素材及原片由使用者提供，本 repo 沒有真人資料，也未指定整體開源授權。
