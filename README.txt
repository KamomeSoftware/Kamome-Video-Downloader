Kamome Video Downloader v0.6.5 Portable
Developer: Kamome Software

Windows向けのシンプルな yt-dlp GUI です。

【ポータブル版】
インストールは不要です。
配布ZIPを任意の書き込み可能なフォルダへ展開し、
KamomeVideoDownloader.exe を実行してください。

本アプリ自身は設定をAppDataやレジストリへ保存しません。
settings.json と yt-dlp の更新確認記録はアプリ本体と同じフォルダに保存されます。
フォルダごと移動・コピーできます。USBメモリ等からの利用も可能です。
削除するときはフォルダを削除するだけです。
※ Windows自身が作成する履歴、セキュリティログ、一時情報等はKamomeの管理対象外です。

主な機能
・URL貼り付け後に動画情報を自動解析
・サムネイル、タイトル、投稿者、長さをプレビュー
・解像度 / FPS / VP9・AV1・H.264等 / 推定容量を表示
・選択した形式をMP4でダウンロード
・動画にサムネイルを埋め込み（サムネイル画像ファイルも保持）
・MP4にタイトル、投稿者/チャンネル、投稿日、元動画URL等のメタデータを埋め込み
・Firefox / Chrome / Edge のCookie利用
・日本語 / English対応（初回はWindowsの言語を自動判定）
・yt-dlpを1日1回自動更新確認
・GitHub ReleasesでKamome Video Downloader本体の最新版を確認
・Ko-fi「開発を支援」リンク

公式情報
Developer: Kamome Software
GitHub: https://github.com/KamomeSoftware/Kamome-Video-Downloader
Support: https://ko-fi.com/kamome92970

注意
本ソフトは Google LLC / YouTube / yt-dlp / FFmpeg と提携・承認関係のない独立したGUIフロントエンドです。
yt-dlpが対応するサイトで利用できますが、各サイトの仕様変更等により利用できない場合があります。
ダウンロードが許可されているコンテンツ、または利用者自身が権利を有するコンテンツに使用してください。
各サービスの利用規約、著作権その他の法令を守って使用してください。

v0.6.5 Portable の変更
・アプリ側のログメッセージをすべて英語に統一
----------------------
・更新通知に「更新ページを開く」「あとで」「このバージョンをスキップ」を追加。
・「あとで」を選ぶと、同じ更新についてその日は再通知しません。
・「このバージョンをスキップ」を選ぶと、その版は以後通知せず、さらに新しい版が公開された場合は再び通知します。
・Kamomeの新しいアプリアイコンをEXE・ウィンドウ・タスクバーに適用。
・前バージョンのウィンドウサイズ・位置・最大化状態の復元機能を継続。

開発者向けビルド
----------------
build_portable.bat を実行してください。
ビルドPCにはPython 3とインターネット接続が必要です。
PyInstallerは一時的な .buildenv に導入し、ビルド後に削除します。
yt-dlpとFFmpegを準備し、PyInstaller --onedir でポータブルフォルダを作成します。

完成物:
output\KamomeVideoDownloader\
output\KamomeVideoDownloader_v0.6.5_Portable.zip

一般利用者のPCにはPython、PyInstaller、Inno Setupは不要です。
