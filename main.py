name: Soccer Bot Auto Run

on:
  schedule:
    # 这里设置每隔 4 小时自动运行一次（你可以根据需要修改 Cron 表达式）
    - cron: '0 */4 * * *'
  workflow_dispatch: # 允许你在网页上手动点一下立即测试

jobs:
  run-bot:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install requests google-generativeai

      - name: Run script
        env:
          ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          TG_BOT_TOKEN: ${{ secrets.TG_BOT_TOKEN }}
          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
        run: python main.py
