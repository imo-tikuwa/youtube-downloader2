# youtube-downloader2

## 環境構築
```
python -m venv venv
.\venv\Scripts\activate.bat
pip install -r requirements.txt
app.py -yid [youtube id] --debug --convert-mp3
```

## オプション
| オプション名 | 内容 |
|---|---|
| -yid, --youtube-id | 動画のID（必須） |
| --debug | デバッグログを出力します |
| --convert-mp3 | ダウンロードした動画をMP3に変換します |
