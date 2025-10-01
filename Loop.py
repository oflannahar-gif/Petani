#!/usr/bin/env python3
# Loop.py
# Script loop masak / mancing dengan kontrol via Saved Messages
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
INTERVAL = 2  # detik

if not API_ID or not API_HASH or not PHONE or not BOT_USERNAME:
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE, BOT_USERNAME ter-set di kunci.env")

client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------- STATE ----------
mode = None                 # "masak" atau "mancing"
payload = None              # untuk masak
mancing_lokasi = None       # untuk mancing
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
            if mode == "masak":
                sender_task = asyncio.create_task(loop_masak())
            elif mode == "mancing":
                sender_task = asyncio.create_task(loop_mancing())
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

# ---------- LOOPS ----------
async def loop_masak():
    global running, payload
    print(f"[{ts()}] Sender loop mulai. Mode=masak, interval={INTERVAL}s")
    try:
        while running and mode == "masak":
            if not payload:
                print(f"[{ts()}] Payload kosong, stop loop.")
                running = False
                break
            try:
                await client.send_message(BOT_USERNAME, payload)
                print(f"[{ts()}] [MASAK] {payload} -> @{BOT_USERNAME}")
            except Exception as e:
                print(f"[{ts()}] [ERROR] {e}")
            await asyncio.sleep(INTERVAL)
    except asyncio.CancelledError:
        pass
    finally:
        print(f"[{ts()}] Sender loop selesai.")

async def loop_mancing():
    global running, mancing_lokasi
    print(f"[{ts()}] Sender loop mulai. Mode=mancing, interval={INTERVAL}s")
    try:
        while running and mode == "mancing":
            if not mancing_lokasi:
                print(f"[{ts()}] Lokasi kosong, stop loop.")
                running = False
                break
            # kirim lokasi
            try:
                await client.send_message(BOT_USERNAME, mancing_lokasi)
                print(f"[{ts()}] [MANCING] Kirim lokasi: {mancing_lokasi}")
            except Exception as e:
                print(f"[{ts()}] [ERROR] Gagal kirim lokasi: {e}")
                await asyncio.sleep(INTERVAL)
                continue

            # tunggu balasan dan klik tombol
            try:
                resp = await client.wait_for(
                    events.NewMessage(from_users=BOT_USERNAME),
                    timeout=2
                )
                if "Tarik Alat Pancing" in [b.text for row in (resp.buttons or []) for b in row]:
                    await resp.click(text="Tarik Alat Pancing")
                    print(f"[{ts()}] [MANCING] {mancing_lokasi} → Tarik Alat Pancing")
                if "tidak memiliki cukup energi" in resp.raw_text.lower():
                    print(f"[{ts()}] STOP otomatis karena energi habis.")
                    running = False
                    await safe_stop_sender()
                    await send_to_saved("⏹ Loop dihentikan (energi habis).")
                    break
            except asyncio.TimeoutError:
                print(f"[{ts()}] [MANCING] Timeout: bot tidak balas.")

            await asyncio.sleep(INTERVAL)
    except asyncio.CancelledError:
        pass
    finally:
        print(f"[{ts()}] Sender loop selesai.")

# ---------- EVENTS ----------
@client.on(events.NewMessage(chats="me"))
async def saved_handler(event):
    global mode, payload, mancing_lokasi, running
    text = (event.raw_text or "").strip()
    if not text:
        return

    cmd = text.lower()

    # start masak
    if cmd == "start masak":
        if not payload:
            await event.reply("❗ Kirim dulu payload masakan/emoji/perintah lalu 'start masak'")
            return
        if running:
            await event.reply("▶️ Sudah berjalan.")
            return
        mode = "masak"
        running = True
        await event.reply(f"▶️ Loop masak dimulai: {payload}")
        await safe_start_sender()
        return

    # start mancing
    if cmd == "start mancing":
        if not mancing_lokasi:
            await event.reply("❗ Kirim dulu nama lokasi mancing lalu 'start mancing'")
            print(f"[{ts()}] Menunggu lokasi mancing...")
            return
        if running:
            await event.reply("▶️ Sudah berjalan.")
            return
        mode = "mancing"
        running = True
        await event.reply(f"▶️ Loop mancing dimulai: {mancing_lokasi}")
        await safe_start_sender()
        return

    # stop
    if cmd == "stop":
        running = False
        await safe_stop_sender()
        await event.reply("⏹ Loop dihentikan.")
        return

    # reset
    if cmd == "reset":
        running = False
        await safe_stop_sender()
        mode, payload, mancing_lokasi = None, None, None
        await event.reply("♻️ Reset selesai, kirim payload/lokasi baru.")
        return

    # kalau bukan command → simpan payload/lokasi
    if mode == "mancing":
        mancing_lokasi = text
        await event.reply(f"✅ Lokasi mancing diset: {mancing_lokasi}\nKetik 'start mancing' untuk mulai.")
        print(f"[{ts()}] Lokasi mancing -> {mancing_lokasi}")
    else:
        payload = text
        await event.reply(f"✅ Payload masak diset: {payload}\nKetik 'start masak' untuk mulai.")
        print(f"[{ts()}] Payload masak -> {payload}")

# ---------- MAIN ----------
async def main():
    await client.start(phone=PHONE)
    print(f"[{ts()}] Client started. Listening Saved Messages...")

    instr = (
        "Bot siap ✅\n\n"
        "Command di Saved Messages:\n"
        "- Kirim teks/emoji → payload masak\n"
        "- Kirim nama lokasi → lokasi mancing\n"
        "- 'start masak' → loop payload masak\n"
        "- 'start mancing' → loop mancing\n"
        "- 'stop' → hentikan loop\n"
        "- 'reset' → hapus payload/lokasi"
    )
    await send_to_saved(instr)
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Exit by user")
