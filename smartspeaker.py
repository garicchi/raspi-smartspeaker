import os, signal
from subprocess import Popen
import subprocess as proc
import urllib.request as request
import urllib.parse as parse
import uuid
import json
import RPi.GPIO as GPIO
from datetime import datetime
from pytz import timezone
from luis_sdk import LUISClient
import random

# 回路でスイッチと繋いだGPIOのピン番号
switch_gpio = 21

# arecord -l で表示されたマイクのカード番号とデバイス番号
mic_card = { mic card id }
mic_device = { mic device id }
# aplay -l で表示されたスピーカーのカード番号とデバイス番号
speaker_card = { speaker card id }
speaker_device = { speaker device id }

# LUISのAPP ID
luis_appid = '{ your luis app id }'
# LUISのAPI KEY
luis_apikey = '{ your luis api key }'
# Bing Speech の API KEY
bing_speech_apikey = '{ your bing speech api key }'
# Bing Video Search の API KEY
bing_search_apikey = '{ your bing video search api key }'


# エントリポイント
def start():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(switch_gpio, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    speech('起動しました。ボタンを押してご用件を発話してください')
    while True:
        # GPIOの入力がHIGHになるまで処理を止める
        GPIO.wait_for_edge(switch_gpio, GPIO.RISING)
        try:
            if stop_youtube():
                continue

            speech('ご用件をどうぞ')
            file = 'record.wav'
            # 録音を開始
            record(file)
            speech('認識しました')
            # 音声認識
            text = recognize(file)
            if text == None:
                speech('音声認識に失敗しました')
                continue
            # 音声認識結果を表示
            print(text)
            # LUISを用いて発話をコマンドに分類する
            r = luis(text)
            # 認識結果からコマンドを実行
            command(r[0],r[1])
        except Exception as e:
            msg = 'エラーが発生しました %s'%e
            print(msg)
            speech(msg)
    GPIO.cleanup()

# open JTalkを使って音声合成
def speech(text):
    # 発話内容をテキストに書き出し
    temp = "speech.txt"
    with open(temp, 'w') as f:
        f.write(text + '\n')

    # 音声合成
    audio = "speech.wav"
    hts = '/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice'
    dic = '/var/lib/mecab/dic/open-jtalk/naist-jdic'
    cmd = "open_jtalk -m %s -x %s -ow %s %s" \
              % (hts, dic, audio, temp)

    proc.check_call(cmd.split(' '))

    # aplayで再生
    cmd = "aplay -D plughw:%d,%d %s" \
              % (speaker_card, speaker_device, audio)
    proc.check_call(cmd.split(' '))


# soxを使って録音を行う
def record(file):
    # 録音開始判定時間
    start = '00:00:00.001'
    # 録音終了判定時間
    end = '00:00:1'
    # -35dBを一定時間以上超えたら録音を開始、-35dBを一定時間以上下回ったら録音を停止する
    cmd = 'sox -c 1 -r 16000 -t alsa plughw:%d,%d %s silence 1 %s -35d 1 %s -35d' \
              % (mic_card, mic_device, file, start, end)
    proc.check_call(cmd.split(' '))


# Bing Speech APIを使った音声認識
def recognize(file):
    # 最初にトークンを取得する
    url = 'https://api.cognitive.microsoft.com/sts/v1.0/issueToken'
    req = request.Request(url)
    req.add_header('Ocp-Apim-Subscription-Key', bing_speech_apikey)
    with request.urlopen(req,data=''.encode('utf-8')) as res:
        token = res.read().decode("utf-8")

    with open(file, 'rb') as f:
        audio = f.read()

    # 取得したトークンを使って音声認識をする
    url = 'https://speech.platform.bing.com/speech/recognition/interactive/cognitiveservices/v1'
    url += '?Version=3.0'
    url += '&language=ja-JP'
    url += '&format=json'
    url += '&requestid=' + str(uuid.uuid4())

    req = request.Request(url)
    req.add_header('Authorization', 'Bearser ' + token)
    req.add_header('Content-Type', 'audio/wav; codec="audio/pcm"; samplerate=16000')
    with request.urlopen(req, data=audio) as res:
        result = res.read().decode('utf-8')
    result = json.loads(result)
    if 'DisplayText' in result:
        text = result['DisplayText']
    else:
        text = None
    return text

# LUISを用いて発話を分類する
def luis(text):
    client = LUISClient(luis_appid, luis_apikey,  True)
    res = client.predict(text)
    # 最も近いインテント(分類コマンド)を取得
    top = res.get_top_intent()
    # 発話の中の要素(エンティティ)を取得
    entities = res.get_entities()
    entities = [(x.get_type(), x.get_name()) for x in entities]
    intent = top.get_name()
    result = (intent,entities)
    return result


# 音声認識結果からコマンドを処理する
def command(intent,entities):
    # intentにはluis.aiで作成したintentの名前が入る
    if intent == 'greeting':
        speech('こんにちは。なにかご要望でしょうか')

    elif intent == 'time':
        t = datetime.now(timezone('UTC'))
        t = t.astimezone(timezone('Asia/Tokyo'))
        t = t.strftime("%Y年%m月%d日 %H時%M分")
        speech('現在%sです' % t)

    elif intent == 'weather':
        weather()

    elif intent == 'music':
        # print('未実装です')
        play_youtube(entities)

    else:
        speech('認識できませんでした')



# 天気を検索する
def weather():
    # cityidはこのサイト(http://weather.livedoor.com/forecast/rss/primary_area.xml)から得られる
    # 天気情報を表示するCITY ID (220040は静岡県浜松市)
    cityid = 220040
    # livedoorのAPIを用いて天気を検索する
    url = 'http://weather.livedoor.com/forecast/webservice/json/v1?city=%s' % cityid
    req = request.Request(url)

    with request.urlopen(req) as res:
        result = res.read().decode('utf-8')
        result = json.loads(result)
    desc = result['description']['text'].split('\n')
    desc = ' '.join(desc[0:2])

    speech('%s %s 以上です' % (result['title'], desc))


# 音楽を再生する子プロセス
music_proc = None
# Bing Search APIを利用して検索したyoutube動画を再生する
def play_youtube(entities):
    global music_proc
    word = [x[1] for x in entities]
    word = ''.join(word)
    # エンティティに何も入っていなかった時のデフォルトの検索ワード
    if len(entities) == 0:
        word = '音楽'
    # music videoをつけて検索をすると音楽がヒットしやすい
    word += ' music video'

    # Bing Video Search APIで動画を検索
    word = parse.quote(word)
    url = 'https://api.cognitive.microsoft.com/bing/v5.0/videos/search?q=%s' % word
    url += '&mkt=ja-jp'

    req = request.Request(url)
    req.add_header('Ocp-Apim-Subscription-Key', bing_search_apikey)
    with request.urlopen(req) as res:
        result = res.read().decode('utf-8')
        result = json.loads(result)

    # 検索結果からyoutubeのビデオのみを抽出し、シャッフル。1番目を再生
    videos = [(x['name'],x['contentUrl']) for x in result['value'] if x['contentUrl'].count('youtube.com') > 0]
    random.shuffle(videos)
    speech('%s を再生します' % videos[0][0])
    cmd = 'youtube-dl "%s" -o - | mplayer -ao alsa:device=plughw=%d.%d - -novideo' \
              % (videos[0][1],speaker_card, speaker_device)
    music_proc = Popen(cmd, shell=True, preexec_fn=os.setsid)

# 音楽の再生を止める
# 音楽が再生されていなかったときはFalseがreturnされる
def stop_youtube():
    global music_proc
    # 現在音楽を再生中なら
    if music_proc and not music_proc.poll():
        # 音楽の再生をとめる
        os.killpg(os.getpgid(music_proc.pid), signal.SIGKILL)
        speech('音楽の再生を停止しました')
        music_proc = None
        return True
    else:
        return False


if __name__ == '__main__':
    start()
