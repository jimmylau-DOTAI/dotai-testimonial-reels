# reels 好評剪輯 Skill

下載整個 Skill，交原片給 AI 助手，就可以分析逐字稿、揀故事、同步真人與螢幕、加字幕／HTML 動畫／聲音，再輸出 1080×1920 MP4。使用者不用手填切點或安裝其他公司 Skills。

需要具備本機檔案與命令工具的 AI 助手，例如 Codex。AI 助手負責語意選材，附帶程式負責轉錄及實際製片；不是另一個自帶 LLM 的獨立應用程式。

## 安裝後直接講

> 用 $dotai-testimonial-reels。原聲係＿＿，真人片係＿＿，錄屏係＿＿。幫我剪一條 90 秒內嘅好評 Reels，用深藍上下雙畫面、完整字幕、HTML 動畫同音效。自行分析素材同選材，直接輸出初剪、文字稿同可重做包。

下載**全部資料夾**，不是只下載一份 Markdown。在 Codex 可放入 `~/.codex/skills/dotai-testimonial-reels/`。第一次執行自動建立 `.runtime/`、安裝依賴及繁體字體；原素材在本機處理，不用 API key。需要 Python 3.9–3.12 及網絡，安裝與模型佔用另見 [執行說明](references/execution.md)。

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
