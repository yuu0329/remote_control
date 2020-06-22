from flask import Flask, request, abort
import paho.mqtt.publish as publish
import os
import json

from linebot import LineBotApi, WebhookHandler

from linebot.exceptions import InvalidSignatureError

from linebot.models import MessageEvent, TextMessage, TextSendMessage


app = Flask(__name__)  # webアプリケーションの初期化

# LINE API関係の環境変数取得
# os.environ[環境変数名]
YOUR_CHANNEL_ACCESS_TOKEN = os.environ['YOUR_CHANNEL_ACCESS_TOKEN']
YOUR_CHANNEL_SECRET = os.environ['YOUR_CHANNEL_ACCESS_SECRET']


#Beebotte関係の環境変数取得
YOUR_BEEBOTTE_TOKEN = os.environ['YOUR_BEEBOTTE_TOKEN']


line_bot_api = LineBotApi(YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

#メッセージリスト
msg_list = [s.encode('utf-8') for s in ['on','off']]

# LINEに通知を送る
def broadcast_line_msg(msg):
    line_bot_api.broadcast(TextSendMessage(text=msg))

# エアコン制御用のMQTTを発行する
def publish_control_msg(msg):
    broadcast_line_msg('get msg')
    publish.single('my_home/remote_control', \
                    msg, \
                    hostname = 'mqtt.beebotte.com', \
                    port = 8833, \
                    auth = {'username':'token:{}'.format(YOUR_BEEBOTTE_TOKEN)}, \
                    tls = {'ca_certs':'mqtt.beebotte.com.pem'})
    broadcast_line_msg('msg publish')


@app.route('/callback',methods=['POST']) # /callbackでデータを送られた時(POST)の処理
def callback():
    # リクエストヘッダーX-Line-Signature(署名が含まれている)を取得
    signature = request.headers['X-Line-Signature']

    body = request.get_data(as_text = True) # データの取得
    app.logger.info('Request body: ' + body)

    # handle webhook body
    try:
        handler.handle(body, signature) # 署名を検証し問題なければhandleに定義されている関数呼び出し
    except InvalidSignatureError:
        abort(400) # errorが起こった場合httpステータスを返す

    return 'OK'

# LINEでMessageEvent(普通のメッセージが送信されたとき)が起こったときdef以下を実行
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.encode('utf-8')

    if msg in msg_list:
        broadcast_line_msg(msg.decode('utf-8'))
        publish_control_msg(msg)
    else:
        broadcast_line_msg('点ける:on\n' \
                            '消す:off')


if __name__=='__main__':
    port = int(os.getenv('PORT'))
    app.run(host='0.0.0.0',port=port)
