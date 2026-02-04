# keiba-local2

ローカルの競馬データ（HTML 等）を管理するリポジトリです。

リポジトリ: https://github.com/TK-cpu-ai/keiba-local2

初回セットアップ（ローカル → GitHub に push）:

```bash
cd /d C:\Users\user\keiba-local2
git init
git add .
git commit -m "Initial import"
git branch -M main
git remote add origin https://github.com/TK-cpu-ai/keiba-local2.git
git push -u origin main
```

別端末で引き継ぐ（クローン）:

```bash
git clone https://github.com/TK-cpu-ai/keiba-local2.git
cd keiba-local2
pip install -r requirements.txt
```

注意:
- プライベートリポジトリの場合は認証（HTTPS または SSH）を行ってください。
- 大きなファイルが多い場合は Git LFS の導入を検討してください。
