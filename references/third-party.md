# 依賴與素材

- Playwright Python 1.55.0：[Microsoft / Playwright](https://github.com/microsoft/playwright-python)，Apache-2.0。安裝時下載相應 Chromium；瀏覽器依其各自授權。
- imageio-ffmpeg 0.6.0：[imageio](https://github.com/imageio/imageio-ffmpeg)，BSD-2-Clause。提供的 FFmpeg binary 依其編譯授權，不能將 Python wrapper 的授權套用到整個 binary。
- faster-whisper 1.2.1：[SYSTRAN](https://github.com/SYSTRAN/faster-whisper)，MIT；模型、CTranslate2、ONNX Runtime 與其他依賴有自己的授權。模型下載不包含本機原音訊。
- NumPy 1.26.4：[NumPy](https://numpy.org/)，BSD-3-Clause；固定版本避免已觀察到的舊 Python／矩陣運算相容問題。
- Noto Sans TC：安裝時從 [Google Fonts](https://github.com/google/fonts/tree/3be1884c48c3e45b52ecc725676a08f87776373e/ofl/notosanstc) 固定 commit 下載，驗 SHA256；SIL Open Font License 1.1，授權檔保存在 runtime。
- 自動底樂與音效是 `scripts/sound.py` 的原創程序合成，沒有附外部音樂、Trailer sample 或私人聲音庫。

程式套件不附 Logo、學生原片、客戶截圖或照片。使用者提供自己的素材。以上依賴授權不是此 repo 的整體開源授權；本 repo 未指定整體開源授權。
