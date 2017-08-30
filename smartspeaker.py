import os, signal
from subprocess import Popen
import subprocess
import urllib.request
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
mic_card = { your mic card }
mic_device = 0
# aplay -l で表示されたスピーカーのカード番号とデバイス番号
speaker_card = { your speaker card }
speaker_device = 0

# LUISのAPP ID
luis_appid = '{ your luis app id }'
# LUISのAPI KEY
luis_apikey = '{ your luis api key }'
# Bing Speech の API KEY
bing_speech_apikey = '{ your bing speech api key }'
# Bing Search の API KEY
bing_search_apikey = '{ your bing search api key }'
# このサイト(http://weather.livedoor.com/forecast/rss/primary_area.xml)から得られる
# 天気情報を表示するCITY ID
weather_city_id = 220040


# エントリポイント
def start():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(switch_gpio, GPIO.IN)

    speech('起動しました。ボタンを押してご用件を発話してください')
    while True:
        # GPIOの入力がHIGHになるまで処理を止める
        GPIO.wait_for_edge(switch_gpio, GPIO.RISING)
        try:
            # 音楽の再生を止める。音楽がなってない場合はFalseとなる
            if stop_youtube():
                continue

            speech('ご用件をどうぞ')
            file = 'record.wav'
            # 録音を開始
            record(file)
            # 音声認識
            text = speech_recognition(file, bing_speech_apikey)
            print('recog: %s'%text)
            # 認識結果からコマンドを実行
            handle_speech(text)
        except Exception as e:
            msg = 'エラーが発生しました %s'%e
            print(msg)
            speech(msg)
    GPIO.cleanup()


# soxを使って録音を行う
def record(file):
    # 録音開始判定時間
    start_duration = '00:00:00.001'
    # 録音終了判定時間
    end_duration = '00:00:1'
    # -35dBを一定時間以上超えたら録音を開始、-35dBを一定時間以上下回ったら録音を停止する
    command = 'sox -c 1 -r 16000 -t alsa plughw:%d,%d %s silence 1 %s -35d 2 %s -35d' \
              % (mic_card, mic_device, file, start_duration, end_duration)
    subprocess.check_call(command.split(' '))


# Bing Speech APIを使った音声認識
def speech_recognition(file, key):
    # 最初にトークンを取得する
    token_url = 'https://api.cognitive.microsoft.com/sts/v1.0/issueToken'
    request = urllib.request.Request(token_url)
    request.add_header('Ocp-Apim-Subscription-Key', key)
    with urllib.request.urlopen(request,data=''.encode('utf-8')) as response:
        token = response.read().decode("utf-8")

    with open(file, 'rb') as f:
        audio_data = f.read()

    # 取得したトークンを使って音声認識をする
    reco_url = 'https://speech.platform.bing.com/speech/recognition/interactive/cognitiveservices/v1'
    reco_url += '?Version=3.0'
    reco_url += '&language=ja-JP'
    reco_url += '&format=json'
    reco_url += '&requestid=' + str(uuid.uuid4())

    request = urllib.request.Request(reco_url)
    request.add_header('Authorization', 'Bearser ' + token)
    request.add_header('Content-Type', 'audio/wav; codec="audio/pcm"; samplerate=16000')
    with urllib.request.urlopen(request, data=audio_data) as response:
        result = response.read().decode('utf-8')
    result_json = json.loads(result)
    text = result_json['DisplayText']
    return text


# open JTalkを使って音声合成
def speech(text):
    # 発話内容をテキストに書き出し
    text_file = "speech.txt"
    with open(text_file, 'w') as f:
        f.write(text + '\n')

    # 音声合成
    audio_file = "speech.wav"
    htsvoice_path = '/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice'
    dic_path = '/var/lib/mecab/dic/open-jtalk/naist-jdic'
    command = "open_jtalk -m %s -x %s -ow %s %s" \
              % (htsvoice_path, dic_path, audio_file, text_file)

    subprocess.check_call(command.split(' '))

    # aplayで再生
    command = "aplay -D plughw:%d,%d %s" \
              % (speaker_card, speaker_device, audio_file)
    subprocess.check_call(command.split(' '))


# 音声認識結果からコマンドを処理する
def handle_speech(text):
    # LUISを用いて発話をコマンドに分類する
    result = luis(luis_appid, luis_apikey, text)

    # 分類結果(intent)からそれぞれの処理をする
    intent = result['intent']
    print('intent: %s'%intent)

    if intent == 'greeting':
        speech('こんにちは。なにかご要望でしょうか')

    elif intent == 'time':
        result = datetime.now(timezone('UTC'))
        result = result.astimezone(timezone('Asia/Tokyo'))
        result = result.strftime("%Y年%m月%d日 %H時%M分")
        speech('現在%sです' % result)

    elif intent == 'weather':
        weather(weather_city_id)

    elif intent == 'music':
        play_youtube(result['entities'], bing_search_apikey)

    else:
        speech('認識できませんでした')

# LUISを用いて発話を分類する
def luis(appid, appkey, text):
    client = LUISClient(appid, appkey, True)
    res = client.predict(text)
    # 最も近いインテント(分類コマンド)を取得
    top = res.get_top_intent()
    # 発話の中の要素(エンティティ)を取得
    entities = res.get_entities()
    entities = [(x.get_type(), x.get_name()) for x in entities]
    top_name = top.get_name()
    result = {
        'intent': top_name,
        'entities': entities
    }
    return result


# 天気を検索する
def weather(cityid):
    # livedoorのAPIを用いて天気を検索する
    endpoint = 'http://weather.livedoor.com/forecast/webservice/json/v1?city=%s' % cityid
    request = urllib.request.Request(endpoint)

    with urllib.request.urlopen(request) as response:
        results = response.read().decode('utf-8')
        results = json.loads(results)
    description = results['description']['text'].split('\n')
    description = ' '.join(description[0:2])

    speech('%s %s 以上です' % (results['title'], description))


# 音楽を再生する子プロセス
music_process = None
# Bing Search APIを利用して検索したyoutube動画を再生する
def play_youtube(entities, search_apikey):
    global music_process
    keyword = [x[1] for x in entities]
    keyword = ''.join(keyword)
    # エンティティに何も入っていなかった時のデフォルトの検索ワード
    if len(entities) == 0:
        keyword = '音楽'
    keyword = urllib.parse.quote(keyword)
    endpoint = 'https://api.cognitive.microsoft.com/bing/v5.0/videos/search?q=%s' % keyword
    endpoint += '&mkt=ja-jp'

    request = urllib.request.Request(endpoint)
    request.add_header('Ocp-Apim-Subscription-Key', search_apikey)
    with urllib.request.urlopen(request) as response:
        results = response.read().decode('utf-8')
        results = json.loads(results)

    videos = [(x['name'],x['contentUrl']) for x in results['value'] if x['contentUrl'].count('youtube.com') > 0]
    random.shuffle(videos)
    speech('%s を再生します' % videos[0][0])
    command = 'youtube-dl "%s" -o - | mplayer -ao alsa:device=plughw=%d.%d - -novideo' \
              % (videos[0][1],speaker_card, speaker_device)
    music_process = Popen(command, shell=True, preexec_fn=os.setsid)

# 音楽の再生を止める
# 音楽が再生されていなかったときはFalseがreturnされる
def stop_youtube():
    global music_process
    # 現在音楽を再生中なら
    if music_process and not music_process.poll():
        # 音楽の再生をとめる
        os.killpg(os.getpgid(music_process.pid), signal.SIGKILL)
        speech('音楽の再生を停止しました')
        music_process = None
        return True
    else:
        return False


if __name__ == '__main__':
    start()

