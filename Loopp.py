# auto_game_multi.py — versi multi-loop fix
# ✅ Multi loop berjalan bersamaan
# ✅ Klik "Tarik Alat Pancing" urut & benar
# ✅ Stop otomatis jika energi habis
# ✅ Sistem Queue aman antar pesan

import os
import asyncio
import random
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ---------------- config (.env) ----------------
load_dotenv("kunci.env")
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
PHONE = os.getenv("PHONE") or ""
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "KampungMaifamBot").lstrip('@')
OWNER_ID = int(os.getenv("OWNER_ID") or 0)

if not API_ID or not API_HASH or not PHONE:
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE ter-set di kunci.env")

# ---------------- logging ----------------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger("auto_game_bot")

# ---------------- client ----------------
SESSION_STRING = os.getenv("TELEGRAM_SESSION")
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------------- QUEUE SYSTEM ----------------
message_queue = asyncio.Queue()

async def safe_send(msg, to=None):
    """Masukkan pesan ke queue"""
    await message_queue.put((msg, to or BOT_USERNAME))

async def message_worker():
    """Kirim pesan satu per satu dengan delay aman"""
    while True:
        msg, dest = await message_queue.get()
        try:
            await client.send_message(dest, msg)
            print(f"[SEND] → {dest}: {msg}")
        except Exception as e:
            print(f"[!] Gagal kirim {msg} ke {dest}: {e}")
        await asyncio.sleep(2)

async def human_sleep(min_s=1.0, max_s=1.5):
    await asyncio.sleep(random.uniform(min_s, max_s))

# ---------------- STATE PER MODE ----------------
state = {
    "masak": {"aktif": False, "kode": None},
    "mancing": {"aktif": False, "lokasi": None},
    "grinding": {"aktif": False, "loops": 0, "count": 0},
    "macul": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180}
}

# ---------------- LOOP MASAK ----------------
async def loop_masak():
    data = state["masak"]
    print(">> Loop Masak dimulai")
    while data["aktif"] and data["kode"]:
        await safe_send(data["kode"])
        await asyncio.sleep(2)
    print(">> Loop Masak berhenti")

# ---------------- LOOP MANCING ----------------
async def loop_mancing():
    data = state["mancing"]
    print(f">> Loop Mancing dimulai di {data['lokasi']}")
    await safe_send(data["lokasi"])  # kirim pertama
    while data["aktif"]:
        await asyncio.sleep(1)
    print(">> Loop Mancing berhenti")

# ---------------- LOOP GRINDING ----------------
grinding_seq = [
    "/tanamGuild_KacangTanah_6000",
    "/KebunGuild_Siram",
    "/kebunGuild_PanenSekarang"
]

async def loop_grinding():
    data = state["grinding"]
    print(f">> Loop Grinding {data['loops']}x dimulai")
    while data["aktif"] and data["count"] < data["loops"]:
        for cmd in grinding_seq:
            if not data["aktif"]:
                break
            await safe_send(cmd)
            await asyncio.sleep(2)
        data["count"] += 1
        print(f">> Grinding ke-{data['count']} selesai")
    data["aktif"] = False
    await safe_send("✅ Grinding selesai", OWNER_ID)

# ---------------- LOOP MACUL ----------------
async def loop_macul():
    data = state["macul"]
    print(f">> Mulai auto Macul {data['tanaman']} ({data['jumlah']} pohon, {data['durasi']}s)")
    while data["aktif"]:
        await safe_send(f"/tanam_{data['tanaman']}_{data['jumlah']}")
        await asyncio.sleep(2)
        await safe_send("/siram")
        await asyncio.sleep(data["durasi"])
        await safe_send("/ambilPanen")
        await asyncio.sleep(3)
    print(">> Loop Macul berhenti")

# ---------------- COMMAND HANDLER ----------------
@client.on(events.NewMessage(from_users=OWNER_ID))
async def cmd_owner(event):
    msg = (event.raw_text or "").strip()
    lmsg = msg.lower()

    print(f">> INPUT OWNER: {msg}")

    # MASAK
    if lmsg == "masak":
        await event.reply("🍳 Mau masak apa?")
        state["masak"].update({"aktif": False, "kode": None})
        return
    if state["masak"]["kode"] is None and lmsg.startswith("/"):
        state["masak"]["kode"] = msg
        state["masak"]["aktif"] = True
        await event.reply(f"Mulai auto masak: {msg}")
        asyncio.create_task(loop_masak())
        return

    # MANCING
    if lmsg == "mancing":
        await event.reply("🎣 Mancing dimana?")
        state["mancing"].update({"aktif": False, "lokasi": None})
        return
    if state["mancing"]["lokasi"] is None and not lmsg.startswith("/"):
        state["mancing"]["lokasi"] = msg
        state["mancing"]["aktif"] = True
        await event.reply(f"Mulai auto-mancing di {msg}")
        asyncio.create_task(loop_mancing())
        return

    # GRINDING
    if lmsg == "grinding":
        await event.reply("🔁 Mau berapa kali grinding?")
        state["grinding"].update({"aktif": False, "loops": 0, "count": 0})
        return
    if state["grinding"]["loops"] == 0 and lmsg.isdigit():
        state["grinding"].update({"aktif": True, "loops": int(lmsg), "count": 0})
        await event.reply(f"Mulai grinding sebanyak {lmsg}x 🔄")
        asyncio.create_task(loop_grinding())
        return

    # MACUL
    if lmsg.startswith("macul"):
        parts = lmsg.split()
        if len(parts) == 3 and parts[2].isdigit():
            _, tanaman, jumlah = parts
            state["macul"].update({
                "aktif": True,
                "tanaman": tanaman,
                "jumlah": int(jumlah),
                "durasi": 180
            })
            await event.reply(f"Mulai auto macul {tanaman} ({jumlah} pohon)")
            asyncio.create_task(loop_macul())
        else:
            await event.reply("Format: macul <tanaman> <jumlah>")
        return

    # STOP
    if lmsg.startswith("stop"):
        mode = lmsg.replace("stop_", "")
        if mode in state:
            state[mode]["aktif"] = False
            await event.reply(f"⏹ Loop {mode} dihentikan.")
        elif lmsg == "stop":
            for v in state.values():
                v["aktif"] = False
            await event.reply("⏹ Semua loop dihentikan.")
        return

# ---------------- BOT REPLY HANDLER ----------------
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_reply(event):
    text = (event.raw_text or "").lower()
    print(f"[BOT] {text[:80]}...")

    # Hentikan semua loop jika energi habis
    if "tidak memiliki cukup energi" in text:
        for v in state.values():
            v["aktif"] = False
        await safe_send("⚠️ Energi habis! Semua loop dihentikan.", OWNER_ID)
        return

    # Loop mancing
    data = state["mancing"]
    if data["aktif"]:
        # klik tombol "Tarik Alat Pancing"
        if event.buttons:
            for row in event.buttons:
                for button in row:
                    if "Tarik Alat Pancing" in button.text:
                        await human_sleep()
                        await button.click()
                        print(">> Klik 'Tarik Alat Pancing'")
                        return

        # kirim ulang lokasi setelah tangkapan
        if "kamu mendapatkan" in text:
            await human_sleep(2, 3)
            await safe_send(data["lokasi"])
            print(f">> Kirim ulang lokasi: {data['lokasi']}")

# ---------------- MAIN ----------------
async def main():
    await client.start(phone=PHONE)
    logger.info("Client started")
    asyncio.create_task(message_worker())
    msg_intro = ("Bot siap ✅\n\nCommand:\n"
                 "- masak → lalu kirim kode masak (/Masak_xx)\n"
                 "- mancing → lalu kirim lokasi\n"
                 "- grinding → lalu kirim jumlah loop\n"
                 "- macul <tanaman> <jumlah>\n"
                 "- stop atau stop_[mode]")
    await safe_send(msg_intro, "me")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
