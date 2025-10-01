#!/usr/bin/env python3
# bot.py
# Simple message-looper controlled via Saved Messages (Saved Messages = "me").
# Requirements:
#   pip install telethon python-dotenv

import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events
from dotenv import load_dotenv

# ---------- CONFIG ----------
load_dotenv("kunci.env")  # file env yang kamu pakai
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
PHONE = os.getenv("PHONE") or ""
BOT_USERNAME = os.getenv("BOT_USERNAME") or ""
# OWNER_ID not required since we use Saved Messages (chats="me")
INTERVAL = 2  # detik antar kirim (fixed 2s, bisa ubah di sini)

if not API_ID or not API_HASH or not PHONE or not BOT_USERNAME:
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE, BOT_USERNAME ter-set di kunci.env")

# ---------- TELETHON CLIENT ----------
client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------- STATE ----------
current_payload = None      # teks / emoji / perintah yang akan di-loop
running = False             # apakah loop sedang berjalan
sender_task = None         # task pengirim (asyncio.Task)
task_lock = asyncio.Lock()  # untuk mencegah create_task ganda

# ---------- HELPERS ----------
def ts():
    return datetime.now().strftime("%H:%M:%S")

async def send_to_saved(msg: str):
    """Kirim pesan ke Saved Messages (hanya untuk memberi tahu owner)"""
    await client.send_message("me", msg)

async def safe_start_sender():
    """Start sender task kalau belum jalan"""
    global sender_task
    async with task_lock:
        if sender_task is None or sender_task.done():
            sender_task = asyncio.create_task(sender_loop())
            print(f"[{ts()}] Sender task dibuat.")

async def safe_stop_sender():
    """Stop sender task"""
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
    """Loop yang mengirim current_payload ke BOT_USERNAME setiap INTERVAL detik."""
    global running, current_payload
    print(f"[{ts()}] Sender loop mulai. Interval = {INTERVAL}s")
    try:
        while running:
            if not current_payload:
                print(f"[{ts()}] Warning: payload kosong — otomatis menghentikan loop.")
                running = False
                break

            try:
                await client.send_message(BOT_USERNAME, current_payload)
                print(f"[{ts()}] [SEND] {current_payload} -> @{BOT_USERNAME}")
            except Exception as e:
                print(f"[{ts()}] [ERROR] Gagal kirim: {e}")

            # tunggu INTERVAL detik, tapi tetap bisa dibatalkan cepat
            try:
                await asyncio.sleep(INTERVAL)
            except asyncio.CancelledError:
                break
    except asyncio.CancelledError:
        pass
    finally:
        print(f"[{ts()}] Sender loop selesai.")

# ---------- EVENTS: Saved Messages kontrol ----------
@client.on(events.NewMessage(chats="me"))
async def saved_handler(event):
    """
    Kontrol lewat Saved Messages (chat "me").
    - Mengirim teks biasa -> set payload
    - 'start' -> mulai loop (butuh payload)
    - 'stop'  -> hentikan loop
    - 'reset' -> hapus payload (set None), hentikan loop
    """
    global current_payload, running

    text = (event.raw_text or "").strip()
    if not text:
        # ignore empty
        return

    lowered = text.lower()

    # Commands
    if lowered == "start":
        if not current_payload:
            await event.reply("❗ Payload belum diset. Kirim teks/emoji/perintah dulu di Saved Messages lalu ketik 'start'.")
            print(f"[{ts()}] Request start tapi payload kosong.")
            return

        if running:
            await event.reply("▶️ Sudah berjalan.")
            print(f"[{ts()}] Start request diterima tapi sudah running.")
            return

        running = True
        await event.reply(f"▶️ Mulai mengirim: {current_payload} setiap {INTERVAL}s ke @{BOT_USERNAME}")
        await safe_start_sender()
        print(f"[{ts()}] START by Saved Messages. Payload: {current_payload}")
        return

    if lowered == "stop":
        if not running:
            await event.reply("⏹ Sudah berhenti.")
            print(f"[{ts()}] Stop request tapi sudah stop.")
            return
        running = False
        await safe_stop_sender()
        await event.reply("⏹ Loop DIBERHENTIKAN")
        print(f"[{ts()}] STOP by Saved Messages.")
        return

    if lowered == "reset":
        # stop and clear payload
        running = False
        await safe_stop_sender()
        current_payload = None
        await event.reply("♻️ Payload di-reset. Kirim teks/emoji baru lalu 'start' untuk mulai.")
        print(f"[{ts()}] RESET by Saved Messages.")
        return

    # Anything else -> treat as payload to send
    # Save the exact text (including emoji or slash commands)
    current_payload = text
    await event.reply(f"✅ Payload disimpan: {repr(current_payload)}\nKetik 'start' untuk mulai, 'reset' untuk ganti.")
    print(f"[{ts()}] Payload diset -> {repr(current_payload)}")

# ---------- STARTUP ----------
async def main():
    # mulai client (akan minta login/OTP jika perlu)
    await client.start(phone=PHONE)
    print(f"[{ts()}] Client started. Listening to Saved Messages for commands.")

    # Kirim instruksi awal ke Saved Messages supaya user tahu flow
    instr = (
        "Bot loop siap ✅\n\n"
        "Cara pakai (pakai Saved Messages):\n"
        "1) Kirim teks/perintah/emoji yang mau di-loop (contoh: /masak_TelurCeplok atau ⛏)\n"
        "2) Kirim 'start' untuk mulai looping setiap 2 detik\n"
        "3) Kirim 'stop' untuk hentikan\n"
        "4) Kirim 'reset' untuk hapus payload dan kirim yang baru\n\n"
        "Note: pesan akan dikirim ke @" + BOT_USERNAME
    )
    # kirim ke Saved Messages
    await send_to_saved(instr)
    print(f"[{ts()}] Instruksi dikirim ke Saved Messages. Tunggu perintahmu...")

    # jalankan client sampai disconnect
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Exiting by user.")
