# テキスト読み上げLINEBOT

<img src="http://qr-official.line.me/L/OIoaB_FTXr.png">

```
mv .env_sample .env
```

ファイルの中身を書き換えてください。
```.env
BITLY_TOKEN=[bitlyのトークンを記載]
CHANNNEL_SERCRET=[Lineのチャンネルシークレットキー記載]
LINE_TOKEN=[Lineトークン記載]
```



ffmpegをDocker(AmazonLinuxImage)を使用してビルド  
ディレクトリ内に含め、zip化  
Lambdaにアップロード(S3からアップロード)
