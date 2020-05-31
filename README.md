# youtube-downloader2

## 環境構築
```
python -m venv venv
.\venv\Scripts\activate.bat
pip install -r requirements.txt
app.py -yid [youtube id] --debug --convert-mp3 --thumb-second 60
```

## オプション
| オプション名 | 内容 |
|---|---|
| -yid, --youtube-id | 動画のID（必須） |
| --debug | デバッグログを出力します。 |
| --convert-mp3 | ダウンロードした動画をMP3に変換します。要ffmpeg |
| --thumb-second | 初期値：1<br>数値のみ指定可能<br>動画から取得するサムネイルの秒数を指定します。<br>取得したサムネイルはMP3のID3タグに埋め込むアルバムアートに使用されます。 |
| --force | ダウンロードディレクトリにMP4やMP3が存在する場合に未確認で上書きします |


## メモ
ダウンロードした動画をMP3形式に変換するにはffmpegが必要です。  
環境変数の設定が済んでいる場合はそのまま使えると思います。  
設定されていない場合はプログラム実行時に開かれるダイアログでffmpeg.exeが存在するディレクトリを設定してください。
