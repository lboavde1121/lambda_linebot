#!/usr/bin/python
# -*- coding: utf-8 -*-
"""This module is Text to Speech."""

import logging
import os
import json
import base64
import hashlib
import hmac
import boto3
from contextlib import closing
import subprocess
from dotenv import load_dotenv
import requests

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Sessionを作成
client = boto3.client('polly')

# リプライ用URL
url = 'https://api.line.me/v2/bot/message/reply'
# トークン
token = os.getenv("LINE_TOKEN")
# リクエストヘッダ
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer %s' % token,
}


def shorten_url(url):
    """Shorten the URL."""
    bitly_url_base = "https://api-ssl.bitly.com/v3/shorten"
    token = os.getenv("BITLY_TOKEN")

    bitly_url = "%s?access_token=%s&longUrl=%s" % (bitly_url_base,
                                                   token, url)
    print(bitly_url)
    bitly_req = requests.get(bitly_url)
    url = bitly_req.json()['data']['url'].replace("http://", "https://")
    return url


def sent_message(event, text):
    """Sent message."""
    body = {
        'replyToken': event['replyToken'],
        'messages': [
                {
                    'type': 'text',
                    'text': text,
                }
            ]
    }
    req = requests.post(url, json=body, headers=headers)
    logger.info(req.text)


def put_s3_object(bucketname, keyname, filename, acl="public-read"):
    """Put S3 Object."""
    s3 = boto3.resource('s3')
    # バケットを取得
    bucket = s3.Bucket(bucketname)
    with open(filename, 'rb') as f:
        # ファイル出力
        bucket.put_object(
            ACL=acl,
            Body=f.read(),
            Key=keyname
        )
    return "Success"


def text_to_speech(event):
    """Text to speech."""
    text = event['message']['text']
    charnum = int(len(text))
    if charnum > 200:
        error_txt = "テキストが長すぎます。200文字以内でお願いします。"
        sent_message(event, error_txt)

    response = client.synthesize_speech(
        OutputFormat='mp3',
        Text=text,
        TextType='text',
        VoiceId='Mizuki'
    )
    logger.info(response)
    path_mp3 = '/tmp/' + event['message']['id'] + '.mp3'
    with open(path_mp3, "wb") as f:
        logger.info("Start Writing")
        with closing(response["AudioStream"]) as stream:
            f.write(stream.read())
            logger.info(os.path.exists(path_mp3))

    m4a_name = event['message']['id'] + '.m4a'
    tmp_m4a = '/tmp/' + m4a_name

    # ffmpeg実行
    ffmpeg_cmd = './ffmpeg_build/bin/ffmpeg -i %s %s' % (path_mp3, tmp_m4a)
    subprocess.call(ffmpeg_cmd, shell=True)

    mp3_name = event['message']['id'] + '.mp3'
    put_s3_object("synthesize-speech-rt1", mp3_name, path_mp3)
    put_s3_object("synthesize-speech-rt1", m4a_name, tmp_m4a)
    os.remove(path_mp3)
    os.remove(tmp_m4a)

    # LINE 投稿
    speech_url = ("https://s3-ap-northeast-1.amazonaws.com/"
                  + "synthesize-speech-rt1/" + m4a_name)
    shoot_url = shorten_url(speech_url)
    logger.info(shoot_url)
    req_json = {
        'replyToken': event['replyToken'],
        'messages': [
            {
                "type": "audio",
                "originalContentUrl": shoot_url,
                "duration": charnum * 166,
            }
        ]
    }
    req = requests.post(url, json=req_json, headers=headers)
    logger.info(req.text)


def lambda_handler(request, context):
    """AWS lambda function."""
    # リクエスト検証
    channel_secret = os.getenv("CHANNNEL_SERCRET")
    logger.info(channel_secret)
    body = request.get('body', '')
    hash = hmac.new(channel_secret.encode('utf-8'),
                    body.encode('utf-8'), hashlib.sha256).digest()
    signature = base64.b64encode(hash).decode('utf-8')

    # # LINE 以外からのアクセスだった場合は処理を終了させる
    if signature != request.get('headers').get('X-Line-Signature', ''):
        logger.info(f'LINE 以外からのアクセス request={request}')
        return {'statusCode': 200, 'body': '{}'}
    logger.info(request)

    # for event in request['events']:
    for event in json.loads(body).get('events', []):
        logger.info(json.dumps(request))
        logger.info(json.dumps(event))
        msg_type = event['message']['type']
        if msg_type == "text":
            # Amaon Pollyで音声作成
            text_to_speech(event)

        if msg_type == "audio":
            # TODO Audio Recognition
            pass

    return {'statusCode': 200, 'body': '{}'}
