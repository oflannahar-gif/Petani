#!/usr/bin/env python3
# Loop.py
# Dual loop bot: masak & mancing, dikontrol lewat Saved Messages.
# pip install telethon python-dotenv

import os
import asyncio
from datetime import datetime
from telethon import TelegramClient, events
from dotenv import load_dotenv

# ---------- CONFIG ----------
load_dotenv("kunci.env")
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
PHONE = os.getenv("PHONE") or ""
BOT_USERNAME = os.getenv("BOT_USERNAME") or ""
INTERVAL = 2  # detik antar aksi

if not API_ID or not API_HASH or not PHONE or not BOT_USERNAME:
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE, BOT_USERNAME ter-set di kunci.env")

client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------- STATE ----------
mode = None
current_payload = None    # untuk masak
mancing_lokasi = None     # untuk mancing
running = False
sender_task = None
task_lock = asyncio.Lock()

# ---------- HELPERS ----------
def ts():
    return datetime.now().strftime("%H:%M:%S")

async def send_to_saved(msg: str):
    await client.send_message("me", msg)

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
    global running, current_payload, mode, mancing_lokasi
    print(f"[{ts()}] Sender loop mulai. Mode={mode}, interval={INTERVAL}s")

    try:
        while running:
            if mode == "masak":
                if not current_payload:
                    print(f"[{ts()}] Payload kosong, stop loop masak.")
                    running = False
                    break
                try:
                    await client.send_message(BOT_USERNAME, current_payload)
                    print(f"[{ts()}] [MASAK] {current_payload}")
                except Exception as e:
                    print(f"[{ts()}] [ERROR masak] {e}")

            elif mode == "mancing":
                if not mancing_lokasi:
                    print(f"[{ts()}] Lokasi kosong, stop loop mancing.")
                    running = False
                    break
                try:
                    # 1. Kirim lokasi
                    await client.send_message(BOT_USERNAME, mancing_lokasi)
                    print(f"[{ts()}] [MANCING] Kirim lokasi: {mancing_lokasi}")

                    # 2. Tunggu balasan bot
                    resp = await client.wait_for(
                        events.NewMessage(from_users=BOT_USERNAME),
                        timeout=5
                    )

                    # 3. Cari tombol Tarik
                    if resp.buttons:
                        clicked = False
                        for row in resp.buttons:
                            for button in row:
                                if "tarik" in (button.text or "").lower():
                                    await resp.click(text=button.text)
                                    print(f"[{ts()}] [MANCING] Klik tombol: {button.text}")
                                    clicked = True
                                    break
                            if clicked:
                                break
                        if not clicked:
                            print(f"[{ts()}] [MANCING] Tidak ada tombol 'Tarik' ditemukan.")
                    else:
                        print(f"[{ts()}] [MANCING] Balasan bot tidak ada tombol.")

                except asyncio.TimeoutError:
                    print(f"[{ts()}] [MANCING] Timeout tunggu balasan bot.")
                except Exception as e:
                    print(f"[{ts()}] [ERROR mancing] {e}")

            # delay antar aksi
            try:
                await asyncio.sleep(INTERVAL)
            except asyncio.CancelledError:
                break
    except asyncio.CancelledError:
        pass
    finally:
        print(f"[{ts()}] Sender loop selesai.")

# ---------- EVENTS ----------
@client.on(events.NewMessage(chats="me"))
async def saved_handler(event):
    global current_payload, running, mode, mancing_lokasi

    text = (event.raw_text or "").strip()
    if not text:
        return
    lowered = text.lower()

    # Mode Masak
    if lowered == "masak":
        mode = "masak"
        await event.reply("👨‍🍳 Masak apa? Kirim perintah/emoji yang mau diloop.")
        return

    if lowered == "start masak":
        if not current_payload:
            await event.reply("❗ Belum ada payload masak. Kirim dulu teks/emoji.")
            return
        mode = "masak"
        running = True
        await safe_start_sender()
        await event.reply(f"▶️ Loop MASAK dimulai: {current_payload} tiap {INTERVAL}s")
        print(f"[{ts()}] START MASAK: {current_payload}")
        return

    # Mode Mancing
    if lowered == "mancing":
        mode = "mancing"
        mancing_lokasi = None
        await event.reply("🎣 Mancing dimana? Kirim nama lokasi.")
        return

    if lowered == "start mancing":
        if not mancing_lokasi:
            await event.reply("❗ Belum ada lokasi. Kirim nama lokasi dulu.")
            return
        mode = "mancing"
        running = True
        await safe_start_sender()
        await event.reply(f"▶️ Loop MANCING dimulai di {mancing_lokasi}, tiap {INTERVAL}s")
        print(f"[{ts()}] START MANCING: {mancing_lokasi}")
        return

    # Stop / Reset
    if lowered == "stop":
        if not running:
            await event.reply("⏹ Sudah berhenti.")
            return
        running = False
        await safe_stop_sender()
        await event.reply("⏹ Loop dihentikan.")
        print(f"[{ts()}] STOP.")
        return

    if lowered == "reset":
        running = False
        await safe_stop_sender()
        mode = None
        current_payload = None
        mancing_lokasi = None
        await event.reply("♻️ Reset selesai. Kirim 'Masak' atau 'Mancing' lagi.")
        print(f"[{ts()}] RESET.")
        return

    # Set payload untuk masak
    if mode == "masak":
        current_payload = text
        await event.reply(f"✅ Payload MASAK diset: {current_payload}\nKetik 'start masak' untuk mulai.")
        print(f"[{ts()}] Payload masak diset: {current_payload}")
        return

    # Set lokasi untuk mancing
    if mode == "mancing" and not mancing_lokasi:
        mancing_lokasi = text
        await event.reply(f"✅ Lokasi MANCING diset: {mancing_lokasi}\nKetik 'start mancing' untuk mulai.")
        print(f"[{ts()}] Lokasi mancing diset: {mancing_lokasi}")
        return

# Stop otomatis kalau energi habis
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_handler(event):
    global running
    text = (event.raw_text or "").lower()
    if "tidak memiliki cukup energi" in text:
        if running:
            running = False
            await safe_stop_sender()
            await send_to_saved("⚠️ Energi habis. Loop otomatis dihentikan.")
            print(f"[{ts()}] STOP otomatis karena energi habis.")

# ---------- STARTUP ----------
async def main():
    await client.start(phone=PHONE)
    print(f"[{ts()}] Client started. Listening Saved Messages...")

    instr = (
        "Bot siap ✅\n\n"
        "Command di Saved Messages:\n"
        "- 'Masak' → pilih payload, lalu 'start masak'\n"
        "- 'Mancing' → pilih lokasi, lalu 'start mancing'\n"
        "- 'stop' → hentikan loop\n"
        "- 'reset' → reset mode/payload\n\n"
        f"Target kirim = @{BOT_USERNAME}"
    )
    await send_to_saved(instr)
    print(f"[{ts()}] Instruksi dikirim ke Saved Messages.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Exiting by user.")
