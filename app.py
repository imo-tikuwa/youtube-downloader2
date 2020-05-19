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
import shutil
import configparser
import tkinter, tkinter.filedialog

DOWNLOAD_DIR = 'downloaded/'
LOG_DIR = 'log' + os.sep
LOG_FILE = LOG_DIR + 'application.log'
CONFIG_FILE_NAME = 'settings.ini'
CONFIG_DEFAULT_SECTION = 'default'
CONFIG_FFMPEG_DIR = 'ffmpeg_dir'

# ログファイル
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
logzero.logfile(LOG_FILE, encoding = "utf-8")
logzero.loglevel(logging.INFO)

# 設定ファイル
config = configparser.ConfigParser()
config.read(CONFIG_FILE_NAME, 'cp932')
if not config.has_section(CONFIG_DEFAULT_SECTION):
    config.add_section(CONFIG_DEFAULT_SECTION)
    config.write(open(CONFIG_FILE_NAME, 'w'))
if config.has_option(CONFIG_DEFAULT_SECTION, CONFIG_FFMPEG_DIR) and not os.path.exists(config.get(CONFIG_DEFAULT_SECTION, CONFIG_FFMPEG_DIR) + os.sep + 'ffmpeg.exe'):
    logger.warning("設定ファイルに保管されているffmpegのディレクトリパスが存在しないため設定を削除します")
    config.remove_option(CONFIG_DEFAULT_SECTION, CONFIG_FFMPEG_DIR)
    config.write(open(CONFIG_FILE_NAME, 'w'))


@click.command()
@click.option('--youtube-id', '-yid', required = True, help = 'youtubeの動画ID(必須)')
@click.option('--debug', is_flag = True, help = "debugログを出力します")
@click.option('--convert-mp3', is_flag = True, help = "mp3に変換して出力します")
def main(youtube_id, debug, convert_mp3):

    if debug:
        logzero.loglevel(logging.DEBUG)

    # ffmpegコマンドのチェック
    if convert_mp3 and not shutil.which('ffmpeg'):
        logger.info("MP3への変換にはffmpegのインストールが必要です。")

        if config.has_option(CONFIG_DEFAULT_SECTION, CONFIG_FFMPEG_DIR):
            ffmpeg_dir = config.get(CONFIG_DEFAULT_SECTION, CONFIG_FFMPEG_DIR)
        else:
            logger.info("ffmpegがインストールされているディレクトリを指定してください")
            tkinter.Tk().withdraw()
            ffmpeg_dir = tkinter.filedialog.askdirectory(initialdir = os.getcwd())
            if ffmpeg_dir == '' or not os.path.exists(ffmpeg_dir + os.sep + 'ffmpeg.exe'):
                logger.error("パスが不正です")
                sys.exit(1)
            config.set(CONFIG_DEFAULT_SECTION, CONFIG_FFMPEG_DIR, ffmpeg_dir)
            config.write(open(CONFIG_FILE_NAME, 'w'))

        os.environ['Path'] += ";{0}".format(ffmpeg_dir)
        logger.debug(os.environ['Path'])
        if not shutil.which('ffmpeg'):
            logger.error("ffmpegの参照が解決できませんでした")
            sys.exit(1)

    try:
        yt = YouTube('https://www.youtube.com/watch?v=' + youtube_id)
    except:
        logger.error("指定のIDの動画は見つかりませんでした")
        sys.exit(1)

    # 解像度の高い順でStreamを取得
    stream = yt.streams.filter(progressive=True, mime_type='video/mp4').order_by('resolution').desc().first()
    if stream is None:
        logger.error("mp4形式の動画が見つかりませんでした。")
        sys.exit(1)

    logger.info("動画が見つかりました。タイトル：{0}".format(stream.title))
    stream.download(DOWNLOAD_DIR, stream.title)
    logger.info("動画の保存に成功しました。")
    # ファイル名として使えない文字を除いた文字列を作成
    stream_title = re.sub(r'[\\/:*?"<>|]+', '', stream.title)
    mp4_file_name = stream_title + '.mp4'

    if convert_mp3:
        mp3_file_name = mp4_file_name.replace('.mp4', '.mp3')
        logger.info("動画をMP3に変換します。ファイル名：{0}".format(mp3_file_name))
        try:
            ffmpeg_stream = ffmpeg.input(DOWNLOAD_DIR + mp4_file_name)
            logger.debug(ffmpeg_stream)
            ffmpeg_stream = ffmpeg.output(ffmpeg_stream, DOWNLOAD_DIR + mp3_file_name)
            ffmpeg.run(ffmpeg_stream, overwrite_output=True)

            logger.info("動画からサムネイルを生成してMP3のID3タグに設定")
            try:
                thumb_file_name = mp4_file_name.replace('.mp4', '.png')
                ffmpeg.input(DOWNLOAD_DIR + mp4_file_name, ss=1).output(DOWNLOAD_DIR + thumb_file_name, vframes=1).run(overwrite_output=True)
                logger.info("サムネイル生成に成功")

                mp3_id3 = eyed3.load(DOWNLOAD_DIR + mp3_file_name)
                mp3_id3.initTag()
                mp3_id3.tag.title = stream.title
                mp3_id3.tag.images.set(eyed3.id3.frames.ImageFrame.FRONT_COVER, open(DOWNLOAD_DIR + thumb_file_name, 'rb').read(), 'image/png')
                logger.debug(mp3_id3)
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