# -*- coding: utf-8 -*-
import sys
import logging
import logzero
from logzero import logger
import click
from pytube import YouTube
from pytube.exceptions import RegexMatchError
import os
import ffmpeg
import re
import eyed3
import shutil
import configparser
import tkinter, tkinter.filedialog
import json

BASE_DIR = os.path.abspath(os.curdir)
DOWNLOAD_DIR = BASE_DIR + os.sep + 'downloaded' + os.sep
DOWNLOADED_LOG_FILE = DOWNLOAD_DIR + '.json'
LOG_DIR = BASE_DIR + os.sep + 'log' + os.sep
LOG_FILE = LOG_DIR + 'application.log'
CONFIG_FILE_NAME = BASE_DIR + os.sep + 'settings.ini'
CONFIG_DEFAULT_SECTION = 'default'
CONFIG_FFMPEG_DIR = 'ffmpeg_dir'

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

# ダウンロード済みファイルを格納するディレクトリと辞書がなければ作成
if not os.path.exists(DOWNLOAD_DIR):
    os.mkdir(DOWNLOAD_DIR)
if not os.path.exists(DOWNLOADED_LOG_FILE):
    json.dump({}, open(DOWNLOADED_LOG_FILE, 'w'), indent=4)


def download_youtube_movie(youtube_id):
    """
    Youtubeから引数のIDを元に動画をダウンロードする
    """
    try:
        yt = YouTube('https://www.youtube.com/watch?v=' + youtube_id)
    except RegexMatchError as e:
        logger.error(e)
        logger.error("指定のIDの動画は見つかりませんでした。動画ID：{0}".format(youtube_id))
        return False, None

    # 解像度の高い順でStreamを取得
    stream = yt.streams.filter(progressive=True, mime_type='video/mp4').order_by('resolution').desc().first()
    if stream is None:
        logger.error("mp4形式の動画が見つかりませんでした。")
        return False, None

    # ファイル名として使えない文字を除いた文字列を作成
    stream_title = re.sub(r'[\\/:*?"<>|~.]+', '', stream.title)
    logger.info("動画が見つかりました。タイトル：{0}".format(stream_title))
    stream.download(DOWNLOAD_DIR, stream_title + '.' + stream.subtype)
    logger.info("動画の保存に成功しました。")

    return True, stream_title


def check_ffmpeg():
    """
    ffmpegが使用可能かチェックする
    パスが通ってない場合はsettings.iniを参照して解決する
    settings.iniに設定が存在しない場合はディレクトリ選択のダイアログを開いて指定してもらう
    パス設定なんかで何か間違った時はFalseを返す
    """
    logger.info('ffmpegが利用可能かチェックします')
    if not shutil.which('ffmpeg'):
        logger.debug("ffmpegのパスが通ってませんでした")
        if config.has_option(CONFIG_DEFAULT_SECTION, CONFIG_FFMPEG_DIR):
            ffmpeg_dir = config.get(CONFIG_DEFAULT_SECTION, CONFIG_FFMPEG_DIR)
            logger.debug("{0}からffmpegのインストールディレクトリを取得しました".format(CONFIG_FILE_NAME))
        else:
            logger.info("MP3への変換にはffmpegのインストールが必要です。ffmpegがインストールされているディレクトリを指定してください")
            tkinter.Tk().withdraw()
            ffmpeg_dir = tkinter.filedialog.askdirectory(initialdir = os.getcwd())
            if ffmpeg_dir == '' or not os.path.exists(ffmpeg_dir + os.sep + 'ffmpeg.exe'):
                logger.error("パスが不正です")
                return False
            config.set(CONFIG_DEFAULT_SECTION, CONFIG_FFMPEG_DIR, ffmpeg_dir)
            config.write(open(CONFIG_FILE_NAME, 'w'))

        os.environ['Path'] += ";{0}".format(ffmpeg_dir)
        logger.debug(os.environ['Path'])
        if not shutil.which('ffmpeg'):
            logger.error("ffmpegの参照が解決できませんでした")
            return False
        logger.debug('ffmpegのパスを解決しました')
    logger.info('ffmpegが利用可能です')
    return True


def is_exist_movie(youtube_id):
    """
    動画がダウンロード済みかどうかを（ファイルパスが解決できるかを含めて）判定する
    """
    downloaded_dict = json.load(open(DOWNLOADED_LOG_FILE, encoding='unicode-escape'))
    return youtube_id in downloaded_dict and os.path.exists(DOWNLOAD_DIR + downloaded_dict[youtube_id] + '.mp4')


def is_exist_mp3(youtube_id):
    """
    引数の動画IDに対応するMP3が存在するか判定する
    """
    downloaded_dict = json.load(open(DOWNLOADED_LOG_FILE, encoding='unicode-escape'))
    return youtube_id in downloaded_dict and os.path.exists(DOWNLOAD_DIR + downloaded_dict[youtube_id] + '.mp3')


def add_download_history(youtube_id, stream_title):
    """
    ダウンロード履歴のファイル（downloaded/.json）を更新する
    """
    downloaded_dict = json.load(open(DOWNLOADED_LOG_FILE, encoding='unicode-escape'))
    downloaded_dict[youtube_id] = stream_title
    json.dump(downloaded_dict, open(DOWNLOADED_LOG_FILE, 'w'), indent=4)


def get_stream_title_by_download_history(youtube_id):
    """
    ダウンロード履歴のファイル（downloaded/.json）から動画タイトルを取得する
    """
    downloaded_dict = json.load(open(DOWNLOADED_LOG_FILE, encoding='unicode-escape'))
    return downloaded_dict[youtube_id]


def convert_mp4_to_mp3(stream_title, thumb_second):
    """
    MP4形式の動画をffmpegを使用してMP3に変換する
    第2引数の秒を元にアルバムアートとして設定する画像を動画から切り出してID3タグに設定する
    """
    # 動画の変換、アルバムアートの設定に失敗したらFalse
    convert_result = True
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
            convert_result = False
            logger.error("サムネイルの設定に失敗")
        logger.info("MP3の作成に成功しました。")
    except:
        convert_result = False
        logger.error("MP3の作成に失敗しました。")
    return convert_result


@click.command()
@click.option('--youtube-id', '-yid', required = True, help = 'youtubeの動画ID(必須)')
@click.option('--debug', is_flag = True, help = "debugログを出力します")
@click.option('--convert-mp3', is_flag = True, help = "mp3に変換して出力します")
@click.option('--thumb-second', required = False, help = 'サムネイル作成対象とする秒数を指定', type = int, default = 1)
@click.option('--force', is_flag = True, help = "ダウンロードディレクトリにMP4やMP3が存在する場合に未確認で上書きします")
def main(youtube_id, debug, convert_mp3, thumb_second, force):

    # ログファイル
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    logzero.logfile(LOG_FILE, encoding = "utf-8")
    logzero.loglevel(logging.INFO)

    if debug:
        logzero.loglevel(logging.DEBUG)
        logger.debug("youtube_id:{0}".format(youtube_id))

    # ffmpegコマンドのチェック
    if convert_mp3:
        check_result = check_ffmpeg()
        if not check_result:
            logger.error('ffmpegのチェックに失敗したためプログラムを終了します。')
            sys.exit(1)

    download_flag = True
    if not force and is_exist_movie(youtube_id):
        print('入力した動画IDの動画は既にダウンロード済みのようです。再度ダウンロードしますか？[y/N]')
        if input() not in ['Y', 'y']:
            download_flag = False

    if download_flag:
        download_result, stream_title = download_youtube_movie(youtube_id)
        if not download_result:
            logger.error('動画のダウンロードに失敗したためプログラムを終了します。')
            sys.exit(1)

        # jsonにダウンロード情報を記録
        add_download_history(youtube_id, stream_title)
    else:
        # jsonから動画のタイトルを取得
        stream_title = get_stream_title_by_download_history(youtube_id)

    if convert_mp3:
        if not force and is_exist_mp3(youtube_id):
            print('ダウンロードした動画に対応するMP3が既に存在します。再度作成しますか？[y/N]')
            if input() not in ['Y', 'y']:
                logger.info("MP3の作成をやめたためプログラムを終了します。")
                sys.exit(0)

        logger.info("動画をMP3に変換します。ファイル名：{0}".format(stream_title + '.mp3'))
        convert_result = convert_mp4_to_mp3(stream_title, thumb_second)
        if not convert_result:
            logger.error("動画のMP3変換に失敗したためプログラムを終了します。")
            sys.exit(1)

if __name__ == "__main__":
    main()