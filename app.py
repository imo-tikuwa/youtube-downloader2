# -*- coding: utf-8 -*-
import logging
import logzero
from logzero import logger
import click
from pytube import YouTube
import os

DOWNLOAD_DIR = 'downloaded/'
LOG_DIR = 'log' + os.sep
LOG_FILE = LOG_DIR + 'application.log'

# ログファイル
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
logzero.logfile(LOG_FILE, encoding = "utf-8")
logzero.loglevel(logging.INFO)

@click.command()
@click.option('--youtube-id', '-yid', required = True, help = 'youtubeの動画ID(必須)')
@click.option('--debug', is_flag = True, help = "debugログを出力します")
@click.option('--convert-mp3', is_flag = True, help = "mp3に変換して出力します")
def main(youtube_id, debug, convert_mp3):

    if debug:
        logzero.loglevel(logging.DEBUG)
        logger.debug("youtube_id:{0}".format(youtube_id))

    try:
        yt = YouTube('https://www.youtube.com/watch?v=' + youtube_id)
    except:
        logger.error("指定のIDの動画は見つかりませんでした")
        return

    # 解像度の高い順でStreamを取得
    stream = yt.streams.filter(progressive=True,mime_type='video/mp4').order_by('resolution').desc().first()
    if stream is None:
        logger.error("mp4形式の動画が見つかりませんでした。")
        return

    logger.info("動画が見つかりました。ファイル名：{0}".format(stream.title))
    logger.debug(stream)
    stream.download(DOWNLOAD_DIR, stream.title)
    logger.info("動画の保存に成功しました。")


if __name__ == "__main__":
    main()