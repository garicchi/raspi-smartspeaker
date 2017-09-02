# raspi-smartspeaker

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
