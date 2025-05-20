import os
from dotenv import load_dotenv

load_dotenv()

token_pay = os.getenv("token_pay_yoomoney")
ym_receiver = os.getenv("ym_receiver")
ADMIN_IDS = [int(os.getenv("ADMIN_ID"))] if os.getenv("ADMIN_ID") else []
MARZBAN_API_URL = os.getenv("MARZBAN_API_URL")
MARZBAN_USER = os.getenv("MARZBAN_USER")
MARZBAN_PASS = os.getenv("MARZBAN_PASS")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SSH_USERNAME = os.getenv("SSH_USERNAME")
SSH_HOST = os.getenv("SSH_HOST")
SSH_PASSWORD = os.getenv("SSH_PASSWORD")

