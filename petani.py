import os
import asyncio
import time
import re
from telethon import TelegramClient, events
from dotenv import load_dotenv

# --- Load data dari .env ---
load_dotenv("kunci.env")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
BOT_USERNAME = os.getenv("BOT_USERNAME")  # target game bot
OWNER_ID = int(os.getenv("OWNER_ID"))

# --- Inisialisasi Telethon ---
client = TelegramClient("Petani_session", API_ID, API_HASH)

# --- Variabel kontrol ---
running_maling = False
running_kebun = False
last_sent = {}  # {kode: timestamp}
DELAY_BETWEEN_CODES = 120   # 2 menit
DELAY_REPEAT_CODE = 3600    # 1 jam

# EXP tracking
exp_now = 0
exp_max = 999999

# --- Baca codes.txt ---
def load_codes():
    if not os.path.exists("codes.txt"):
        return []
    with open("codes.txt", "r") as f:
        codes = [line.strip() for line in f if line.strip()]
    return codes

# --- Parse EXP dari pesan /status ---
def parse_exp(text):
    global exp_now, exp_max
    match = re.search(r"EXP:\s*([\d,]+)/([\d,]+)", text)
    if match:
        exp_now = int(match.group(1).replace(",", ""))
        exp_max = int(match.group(2).replace(",", ""))
        print(f"[STATUS] EXP {exp_now}/{exp_max}")

# --- Tambah EXP dan log ---
def add_exp(amount, sumber=""):
    global exp_now, exp_max
    exp_now += amount
    print(f">> +{amount} EXP → {exp_now}/{exp_max} {sumber}")

# --- Cek EXP & levelup ---
async def check_levelup():
    global exp_now, exp_max
    if exp_now >= exp_max:
        try:
            await client.send_message(BOT_USERNAME, "/levelup")
            print("🎉 [LEVELUP] Kirim /levelup (EXP penuh)")
            await asyncio.sleep(3)
            await client.send_message(BOT_USERNAME, "/status")
        except Exception as e:
            print(f"[!] Gagal levelup: {e}")

# --- Task maling ---
async def auto_maling():
    global running_maling
    while True:
        if running_maling:
            codes = load_codes()
            for code in codes:
                now = time.time()
                last_time = last_sent.get(code, 0)
                if now - last_time >= DELAY_REPEAT_CODE:
                    try:
                        await client.send_message(BOT_USERNAME, code)
                        print(f"[MALING] Kirim kode: {code}")
                        last_sent[code] = now
                    except Exception as e:
                        print(f"[!] Gagal kirim {code}: {e}")
                    await asyncio.sleep(DELAY_BETWEEN_CODES)
                else:
                    continue
        else:
            await asyncio.sleep(5)

# --- Task kebun wortel ---
async def auto_kebun():
    global running_kebun

    while True:
        if running_kebun:
            try:
                # Tanam
                await client.send_message(BOT_USERNAME, "/tanam_Wortel_25")
                add_exp(75, "[KEBUN] Tanam wortel")
                print("[KEBUN] Tanam wortel sukses")
                await asyncio.sleep(2)

                # Siram
                await client.send_message(BOT_USERNAME, "/siram")
                add_exp(50, "[KEBUN] Siram tanaman")
                print("[KEBUN] Siram sukses")
                await asyncio.sleep(2)

                # Tunggu panen
                print("[KEBUN] Menunggu 185 detik sampai panen...")
                await asyncio.sleep(185)

                # Panen
                await client.send_message(BOT_USERNAME, "/ambilPanen")
                add_exp(375, "[KEBUN] Panen wortel")
                print("[KEBUN] Panen sukses")

                # Cek level up
                await check_levelup()

                await asyncio.sleep(2)

            except Exception as e:
                print(f"[!] Error kebun: {e}")
                await asyncio.sleep(5)
        else:
            await asyncio.sleep(5)

# --- Handler pesan masuk dari owner ---
@client.on(events.NewMessage(chats=OWNER_ID))
async def handler_owner(event):
    global running_maling, running_kebun
    msg = event.raw_text.lower().strip()

    if msg == "start maling":
        running_maling = True
        await event.reply("✅ Loop MALING dimulai")
        print(">> Maling STARTED")

    elif msg == "stop maling":
        running_maling = False
        await event.reply("⏹ Loop MALING dihentikan")
        print(">> Maling STOPPED")

    elif msg == "start kebun":
        running_kebun = True
        await event.reply("✅ Loop KEBUN dimulai")
        print(">> Kebun STARTED")

    elif msg == "stop kebun":
        running_kebun = False
        await event.reply("⏹ Loop KEBUN dihentikan")
        print(">> Kebun STOPPED")

    elif msg == "status":
        await client.send_message(BOT_USERNAME, "/status")

# --- Handler pesan dari game bot (baca EXP & log lain) ---
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def handler_bot(event):
    text = event.raw_text
    if "EXP:" in text:
        parse_exp(text)
    if "berhasil meningkatkan level" in text.lower():
        print("🎉 [LEVELUP] Level naik! EXP direset")

# --- Main ---
async def main():
    print(">> Bot siap jalan.")
    print("   Perintah: 'start maling' / 'stop maling'")
    print("             'start kebun'  / 'stop kebun'")
    await client.send_message(BOT_USERNAME, "/status")
    asyncio.create_task(auto_maling())
    asyncio.create_task(auto_kebun())
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
