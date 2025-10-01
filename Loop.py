#!/usr/bin/env python3
# Loop.py
# Bot sederhana: bisa pilih mode "Masak" atau "Mancing".
# Kontrol via Saved Messages ("me").
# ----------------------------------------
# pip install telethon python-dotenv

import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events, Button
from dotenv import load_dotenv

# ---------- CONFIG ----------
load_dotenv("kunci.env")
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
PHONE = os.getenv("PHONE") or ""
BOT_USERNAME = os.getenv("BOT_USERNAME") or ""
INTERVAL = 2  # detik antar kirim

if not API_ID or not API_HASH or not PHONE or not BOT_USERNAME:
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE, BOT_USERNAME ter-set di kunci.env")

# ---------- TELETHON CLIENT ----------
client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------- STATE ----------
mode = None              # "masak" atau "mancing"
payload = None           # teks masakan atau lokasi mancing
running = False
sender_task = None
task_lock = asyncio.Lock()

# ---------- HELPERS ----------
def ts():
    return datetime.now().strftime("%H:%M:%S")

async def safe_start_sender():
    global sender_task
    async with task_lock:
        if sender_task is None or sender_task.done():
            sender_task = asyncio.create_task(sender_loop())
            print(f"[{ts()}] Sender task dibuat.")

async def safe_stop_sender():
    global sender_task
    async with task_lock:
        if sender_task and not sender_task.done():
            sender_task.cancel()
            try:
                await sender_task
            except asyncio.CancelledError:
                pass
            sender_task = None
            print(f"[{ts()}] Sender task dihentikan.")

# ---------- SENDER LOOP ----------
async def sender_loop():
    global running, payload, mode
    print(f"[{ts()}] Sender loop mulai. Mode={mode}, interval={INTERVAL}s")

    try:
        if mode == "mancing":
            # kirim lokasi dulu sekali biar tombol muncul
            await client.send_message(BOT_USERNAME, payload)
            print(f"[{ts()}] [MANCING] Lokasi dikirim: {payload}")
            await asyncio.sleep(1)

        while running:
            try:
                if mode == "masak":
                    await client.send_message(BOT_USERNAME, payload)
                    print(f"[{ts()}] [MASAK] {payload}")

                elif mode == "mancing":
                    # klik tombol "Tarik Alat Pancing"
                    await client.send_message(BOT_USERNAME, "Tarik Alat Pancing")
                    print(f"[{ts()}] [MANCING] {payload} → Tarik Alat Pancing")

            except Exception as e:
                print(f"[{ts()}] [ERROR] {e}")

            try:
                await asyncio.sleep(INTERVAL)
            except asyncio.CancelledError:
                break
    except asyncio.CancelledError:
        pass
    finally:
        print(f"[{ts()}] Sender loop selesai.")

# ---------- HANDLER SAVED MESSAGES ----------
@client.on(events.NewMessage(chats="me"))
async def handler(event):
    global mode, payload, running

    text = (event.raw_text or "").strip()
    if not text:
        return

    lower = text.lower()

    # Reset
    if lower == "reset":
        running = False
        await safe_stop_sender()
        mode, payload = None, None
        await event.reply("♻️ Reset selesai. Ketik 'Masak' atau 'Mancing' untuk mulai lagi.")
        print(f"[{ts()}] RESET by user.")
        return

    # Stop
    if lower == "stop":
        if not running:
            await event.reply("⏹ Sudah berhenti.")
        else:
            running = False
            await safe_stop_sender()
            await event.reply("⏹ Loop DIBERHENTIKAN.")
        return

    # Mode pilih
    if lower == "masak":
        mode, payload = "masak", None
        await event.reply("🍳 Masak apa?")
        print(f"[{ts()}] Mode diset ke MASAK. Menunggu payload...")
        return

    if lower == "mancing":
        mode, payload = "mancing", None
        await event.reply("🎣 Mancing dimana?")
        print(f"[{ts()}] Mode diset ke MANCING. Menunggu lokasi...")
        return

    # Isi payload
    if mode == "masak" and payload is None:
        payload = text
        running = True
        await event.reply(f"✅ Masak {payload} setiap {INTERVAL}s dimulai.")
        print(f"[{ts()}] Payload MASAK diset: {payload}")
        await safe_start_sender()
        return

    if mode == "mancing" and payload is None:
        payload = text
        running = True
        await event.reply(f"✅ Mancing di {payload} dimulai. Interval {INTERVAL}s.")
        print(f"[{ts()}] Lokasi MANCING diset: {payload}")
        await safe_start_sender()
        return

    # Kalau sudah ada payload dan user kirim teks lagi
    await event.reply("❗ Gunakan 'reset' dulu untuk ganti mode atau payload.")

# ---------- STARTUP ----------
async def main():
    await client.start(phone=PHONE)
    print(f"[{ts()}] Client started. Listening Saved Messages...")

    instr = (
        "Bot siap ✅\n\n"
        "Command di Saved Messages:\n"
        "- Ketik 'Masak' → pilih menu masakan\n"
        "- Ketik 'Mancing' → pilih lokasi mancing\n"
        "- 'stop' → hentikan loop\n"
        "- 'reset' → hapus mode & payload\n"
    )
    await client.send_message("me", instr)
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Exiting by user.")
