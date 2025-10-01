#!/usr/bin/env python3
# bot.py
# Dual loop bot: masak & mancing, dikontrol lewat Saved Messages.
# Requirements:
#   pip install telethon python-dotenv

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
INTERVAL = 2  # detik antar kirim

if not API_ID or not API_HASH or not PHONE or not BOT_USERNAME:
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE, BOT_USERNAME ter-set di kunci.env")

client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------- STATE ----------
mode = None               # "masak" atau "mancing"
current_payload = None    # untuk masak → string perintah
mancing_lokasi = None     # untuk mancing → nama lokasi
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
                    # kirim lokasi
                    await client.send_message(BOT_USERNAME, mancing_lokasi)
                    print(f"[{ts()}] [MANCING] Kirim lokasi: {mancing_lokasi}")

                    # tunggu balasan bot yg berisi tombol
                    resp = await client.wait_for(
                        events.NewMessage(from_users=BOT_USERNAME),
                        timeout=5
                    )

                    # klik tombol "Tarik Alat Pancing"
                    try:
                        await resp.click(text="Tarik Alat Pancing")
                        print(f"[{ts()}] [MANCING] Tarik Alat Pancing diklik")
                    except Exception:
                        print(f"[{ts()}] [MANCING] Tombol tidak ditemukan.")

                except asyncio.TimeoutError:
                    print(f"[{ts()}] [MANCING] Timeout tunggu balasan bot.")
                except Exception as e:
                    print(f"[{ts()}] [ERROR mancing] {e}")

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

    # Command: START MASAK
    if lowered == "start masak":
        if not current_payload:
            await event.reply("❗ Payload masak kosong. Kirim perintah/emoji dulu.")
            return
        mode = "masak"
        running = True
        await safe_start_sender()
        await event.reply(f"▶️ Mulai loop MASAK: {current_payload} setiap {INTERVAL}s")
        print(f"[{ts()}] START MASAK: {current_payload}")
        return

    # Command: START MANCING
    if lowered == "start mancing":
        mode = "mancing"
        mancing_lokasi = None
        await event.reply("🎣 Mancing dimana? Kirim nama lokasi (contoh: Sungai Badabu).")
        print(f"[{ts()}] Menunggu lokasi mancing...")
        return

    # Command: STOP
    if lowered == "stop":
        if not running:
            await event.reply("⏹ Sudah berhenti.")
            return
        running = False
        await safe_stop_sender()
        await event.reply("⏹ Loop DIBERHENTIKAN")
        print(f"[{ts()}] STOP.")
        return

    # Command: RESET
    if lowered == "reset":
        running = False
        await safe_stop_sender()
        mode = None
        current_payload = None
        mancing_lokasi = None
        await event.reply("♻️ Payload direset. Kirim baru lagi.")
        print(f"[{ts()}] RESET.")
        return

    # Payload utk MASAK
    if mode != "mancing":
        current_payload = text
        await event.reply(f"✅ Payload MASAK disimpan: {repr(current_payload)}\nKetik 'start masak' untuk mulai.")
        print(f"[{ts()}] Payload masak diset -> {repr(current_payload)}")
        return

    # Payload utk MANCING → lokasi
    if mode == "mancing" and not mancing_lokasi:
        mancing_lokasi = text
        running = True
        await safe_start_sender()
        await event.reply(f"🎣 Lokasi MANCING diset: {mancing_lokasi}\n▶️ Loop mancing dimulai tiap {INTERVAL}s")
        print(f"[{ts()}] Lokasi mancing -> {mancing_lokasi}")
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
        "Command:\n"
        "- Kirim teks/perintah/emoji → jadi payload MASAK\n"
        "- 'start masak' → mulai loop masak\n"
        "- 'start mancing' → pilih lokasi lalu loop mancing\n"
        "- 'stop' → stop loop\n"
        "- 'reset' → reset payload/lokasi\n\n"
        "Note: target kirim = @" + BOT_USERNAME
    )
    await send_to_saved(instr)
    print(f"[{ts()}] Instruksi dikirim ke Saved Messages.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Exiting by user.")
