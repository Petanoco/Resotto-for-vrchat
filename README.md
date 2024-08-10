# README.md

チャンネルに画像を貼ると自動で指定サイズまで縮小してくれるDiscordBotです。

## 導入方法

ローカルで動かす想定なので、各自でBotの作成が必要です
1. Botの作成・登録
   1. [Dicord Developer Portal](https://discord.com/developers/applications)を開く
   2. New Application ボタンから新規Botを作る
   3. Botの設定画面が開くので、Botタブに移動して以下の項目を確認する
      - `Build-A-Bot/TOKEN`: Reset Tokenボタンを押してアクセストークンを生成し、控えておく
      - `Privileged Gateway Intents/Message Content Intent`: 有効にする
   4. OAuth2タブに移動して、Botをサーバーへ登録するためのURLを生成する
      1. `SCOPES`の`bot`にチェック
      2. `Bot Permissions`が開くので`Send Messages`, `Attach Files`にチェック
      3. `Generated URL`に登録用URLが生成される
   5. 4.で取得したURLを開き、好きなサーバーにBotを追加する
2. Botを実行する
   1. `config/config.json`を開き、`token`に1.3で控えたアクセストークンを貼り付ける
   2. `GoldenBot.exe`を実行する
3. おけまる🕊️

## 使い方

Botが参加しているサーバー(チャンネルホワイトリストが有効の場合は登録したチャンネル)で解像度の大きい画像を貼ると、自動的に縮小した画像でリプライされます.

## config.jsonの項目

| 項目                        | 説明                                                                                                                            |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| token                       | アクセストークン                                                                                                                |
| presence                    | 「VRChatをプレイ中」みたいに表示されるBotのステータス                                                                           |
| target_resolution           | 変換先の解像度                                                                                                                  |
| max_file_count              | 複数の添付ファイルがある場合に何枚まで処理するか                                                                                |
| log_level                   | ログレベル</br>NOTSET / DEBUG / INFO / WARN / ERROR / FATAL                                                                     |
| quality                     | 0~5で縮小アルゴリズムを指定します 大きい方が高品質</br>5:Lanczos / 4:Bicubic / 3:Hamming / 2:Bilinear / 1:BoxFilter / 0:Nearest |
| use_timestamped_logfilename | ログファイルを実行毎に別名で保存するかどうか                                                                                    |

## コマンド

- `/add_resize_channel`: コマンドを実行したチャンネルをホワイトリスト(is_whitelistedがTrueの場合のみ)へ追加します
- `/remove_resize_channel`: コマンドを実行したチャンネルをホワイトリスト(is_whitelistedがTrueの場合のみ)から削除します
