# reels 好評剪輯 Skill

將學生／客戶真實分享，剪成睇得見工作轉變嘅 Reels。參照 Edmond Wong 案例，保留真人原聲、作品影片、完整字幕、HTML 動畫同音效節奏。

這是私人方法備份，供 Jimmy／獲授權同事使用。包含剪輯 Skill 與參照參數；原片、學生截圖、字體、Logo、音樂、SFX、帳戶憑證及完整重做包留在原 Project。

## 點樣用

讀 [SKILL.md](SKILL.md)，新個案先填 [剪輯計劃](assets/case-plan.md)。在支援本機 Skills 的 Codex 環境，可將本資料夾放入 `~/.codex/skills/dotai-testimonial-reels/`；其他工具按自己的 Skill 安裝規則處理。

已有同名 Skill 時先比較版本，保留原 canonical／symlink，勿盲目覆寫。Jimmy 本機已安裝的 Skill 正本仍在 Obsidian Vault，GitHub 是選定方法的匯出快照。

直接講：

> 用 $dotai-testimonial-reels，參照 Edmond 好評 Reels。今次學生係＿＿，原片係＿＿。先交逐句文字稿、來源時間碼同畫面配搭；確認後剪一條 90 秒精華。

## 一條故事點樣砌

1. **Hook＋身份**：先聽學生講最有力的一句，介紹課程／期數／姓名。
2. **作品證明**：真實草稿 → 圖則／3D；PPT 提案、Excel 報價要有閱讀時間。
3. **工作转變**：AI 準備資料與初稿，人保留覆核、判斷及見客。
4. **Skill 流程**：清楚顯示一個流程串起哪些步驟，不把不同項目當一次全自動完成。
5. **公司用途與再利用**：Company OS → 案例圖文；CTA 用當次已確認內容。

## Edmond 參照

- [案例讀法與限制](references/edmond-case.md)
- [節奏／排位／HTML／聲音與避坑](references/customer-testimonial-workflow.md)
- [v27 參照參數](examples/edmond-v27-preset.json)：1080×1920、30fps、87.733 秒，已加速 1.1 倍；不可再加速一次。

參數是該案例的排位，需按新人物、作品及平台介面重新驗收。GitHub 不含影片和渲染器，不能單靠這套方法直接重建 Edmond 成片。

## 製作依賴

此套件可獨立閱讀和規劃剪輯；實際製片要有以下能力。Jimmy 本機的對應 Skills 已另外管理，這裡沒有複製全部依賴。

- **分鏡**：`dotai-reels-storyboard`，逐句來源／故事／切點。
- **HTML 分鏡**：`reels-html`，畫面、HTML 和分鏡 manifest。
- **合成與混音**：`dotai-reels-overlay`，上下真實畫面、字幕、HTML 動態、聲音。
- **渲染**：`hyperframes`，按其實際版本使用；Edmond 參照版本是 0.8.123，不當作最新版本建議。
- 素材工具：FFmpeg／ffprobe、Node.js、Python；按選定 Project 鎖定實際版本。
- 素材：已配對的 A 真人有聲／B 螢幕無聲、逐字稿、合法可用品牌／字體／聲音。

缺某個製作 Skill 時先定位或安裝相應方法，勿宣稱已具備渲染／發布能力。現有 Edmond 重做需取原 Project 的 `rebuild-kit-v27`，在該包執行 `python3 rebuild.py --rebuild`；本 repo 沒有此腳本。

## 更新與驗收

Vault 是方法正本；修改後重新匯出快照，以 Git commit／PR 記錄差異。檢查 Skill 結構、所有相對引用及檔案 hash；真正製片另查 MP4、字幕、聲音和可重建性。

技術 QA 不等於逐字聽校或成效證明。學生自述數字不能變成課程保證；生成作品、成交及實際發佈分開核對。

本套件沒有附開源授權；私人備份不代表第三方素材可以再分發。
