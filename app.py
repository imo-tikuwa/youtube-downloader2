# -*- coding: utf-8 -*-
import sys
import logging
import logzero
from logzero import logger
import click
from pytube import YouTube
import os
import ffmpeg
import re
import eyed3
import json

DOWNLOAD_DIR = 'downloaded' + os.sep
DOWNLOADED_LOG_FILE = DOWNLOAD_DIR + '.json'
LOG_DIR = 'log' + os.sep
LOG_FILE = LOG_DIR + 'application.log'

# ログファイル
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
logzero.logfile(LOG_FILE, encoding = "utf-8")
logzero.loglevel(logging.INFO)

# ダウンロード済みファイルの辞書
if not os.path.exists(DOWNLOADED_LOG_FILE):
    json.dump({}, open(DOWNLOADED_LOG_FILE, 'w'), indent=4)
downloaded_dict = json.load(open(DOWNLOADED_LOG_FILE, encoding='unicode-escape'))


def download_youtube_movie(youtube_id):
    """
    Youtubeから引数のIDを元に動画をダウンロードする
    """
    try:
        yt = YouTube('https://www.youtube.com/watch?v=' + youtube_id)
    except:
        logger.error("指定のIDの動画は見つかりませんでした")
        return False, None

    # 解像度の高い順でStreamを取得
    stream = yt.streams.filter(progressive=True, mime_type='video/mp4').order_by('resolution').desc().first()
    if stream is None:
        logger.error("mp4形式の動画が見つかりませんでした。")
        return False, None

    logger.info("動画が見つかりました。タイトル：{0}".format(stream.title))
    stream.download(DOWNLOAD_DIR, stream.title)
    logger.info("動画の保存に成功しました。")
    # ファイル名として使えない文字を除いた文字列を作成
    stream_title = re.sub(r'[\\/:*?"<>|]+', '', stream.title)

    return True, stream_title


@click.command()
@click.option('--youtube-id', '-yid', required = True, help = 'youtubeの動画ID(必須)')
@click.option('--debug', is_flag = True, help = "debugログを出力します")
@click.option('--convert-mp3', is_flag = True, help = "mp3に変換して出力します")
@click.option('--thumb-second', required = False, help = 'サムネイル作成対象とする秒数を指定', type = int, default = 1)
def main(youtube_id, debug, convert_mp3, thumb_second):

    if debug:
        logzero.loglevel(logging.DEBUG)
        logger.debug("youtube_id:{0}".format(youtube_id))

    download_flag = True
    if youtube_id in downloaded_dict and os.path.exists(DOWNLOAD_DIR + downloaded_dict[youtube_id] + '.mp4'):
        print('入力した動画IDの動画は既にダウンロード済みのようです。再度ダウンロードしますか？[y/N]')
        if input() not in ['Y', 'y']:
            download_flag = False

    if download_flag:
        download_result, stream_title = download_youtube_movie(youtube_id)
        if not download_result:
            sys.exit(1)

        # jsonにダウンロード情報を記録
        downloaded_dict[youtube_id] = stream_title
        json.dump(downloaded_dict, open(DOWNLOADED_LOG_FILE, 'w'), indent=4)
    else:
        # jsonから動画のタイトルを取得
        stream_title = downloaded_dict[youtube_id]

    if convert_mp3:
        if youtube_id in downloaded_dict and os.path.exists(DOWNLOAD_DIR + downloaded_dict[youtube_id] + '.mp3'):
            print('ダウンロードした動画に対応するMP3が既に存在します。再度作成しますか？[y/N]')
            if input() not in ['Y', 'y']:
                logger.info("MP3の作成をやめたためプログラムを終了します。")
                sys.exit(0)

        logger.info("動画をMP3に変換します。ファイル名：{0}".format(stream_title + '.mp3'))
        try:
            ffmpeg_stream = ffmpeg.input(DOWNLOAD_DIR + stream_title + '.mp4')
            ffmpeg_stream = ffmpeg.output(ffmpeg_stream, DOWNLOAD_DIR + stream_title + '.mp3')
            ffmpeg.run(ffmpeg_stream, overwrite_output=True, quiet=True)

            logger.info("動画からサムネイルを生成してMP3のID3タグに設定")
            try:
                ffmpeg.input(DOWNLOAD_DIR + stream_title + '.mp4', ss=1).output(DOWNLOAD_DIR + stream_title + '.png', vframes=1, ss=thumb_second).run(overwrite_output=True, quiet=True)
                logger.info("サムネイル生成に成功")

                mp3_id3 = eyed3.load(DOWNLOAD_DIR + stream_title + '.mp3')
                mp3_id3.initTag()
                mp3_id3.tag.title = stream_title
                mp3_id3.tag.images.set(eyed3.id3.frames.ImageFrame.FRONT_COVER, open(DOWNLOAD_DIR + stream_title + '.png', 'rb').read(), 'image/png')
                mp3_id3.tag.save(encoding='utf-8', version=eyed3.id3.ID3_V2_3)
                logger.info("サムネイルの設定に成功")
            except:
                logger.error("サムネイルの設定に失敗")

            logger.info("MP3の作成に成功しました。")
        except:
            logger.error("MP3の作成に失敗しました。")
            sys.exit(1)

if __name__ == "__main__":
    main()