# ラズパイで実現するAIスピーカー

## 日経Linux及びラズパイマガジン読者の方へ
日経Linux11月号およびラズパイマガジン12月号の音楽再生の部分で必要なコードは```smartspeaker.py```の以下の部分となります

```py
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
```

また、ソースコード全体としては```smartspeaker.py```に載っているのでご参照ください。

## no module named RPiとエラーが出た方
root権限で実行してみてください
```sh
sudo python3 smartspeaker.py
```

## require
- raspberry pi (Raspbian)
- Bing Speech API Key
- Bing Video Search API Key
- LUIS App Id
- LUIS API Key
- 構築済みLUIS学習モデル

## install
```sh
sudo pip3 install git+https://github.com/Microsoft/Cognitive-LUIS-Python.git
sudo pip3 install pytz
sudo apt-get install -y sox
sudo apt-get install -y open-jtalk-mecab-naist-jdic hts-voice-nitech-jp-atr503-m001 open-jtalk
sudo apt-get install -y mplayer
sudo curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl
sudo chmod u+rx /usr/local/bin/youtube-dl
```

replace

- { mic card id } → arecord -lで取得したマイクのカードID
- { mic device id } → arecord -lで取得したマイクのデバイスID
- { speaker card id } → aplay -lで取得したスピーカーのカードID
- { speaker device id } → aplay -lで取得したスピーカーのデバイスID
- { your luis app id } → luis.aiで取得したLUISのApp Id
- { your luis api key } → luis.aiで取得したLUISのAPI Key
- { your bing speech api key } → Cognitive Servicesのトライアルページで取得したBing Speech APIのAPI Key
- { your bing video search api key } → Cognitive Servicesのトライアルページで取得したBing Video Search APIのAPI Key
