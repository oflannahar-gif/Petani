#!/usr/bin/env python3
# Loop.py
# Kontrol via Saved Messages ("me")
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
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE, BOT_USERNAME sudah ada di kunci.env")

client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------- STATE ----------
mode = None              # "masak" | "mancing" | None
payload = None           # text masak atau lokasi mancing
running = False
task = None
lock = asyncio.Lock()

# ---------- UTILS ----------
def ts():
    return datetime.now().strftime("%H:%M:%S")

async def send_to_me(msg):
    await client.send_message("me", msg)

async def stop_loop(msg=None):
    global running, task, mode, payload
    running = False
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    task = None
    mode = None
    payload = None
    if msg:
        await send_to_me(msg)
    print(f"[{ts()}] Loop STOP. {msg or ''}")

# ---------- LOOPS ----------
async def masak_loop():
    global running, payload
    print(f"[{ts()}] Loop MASAK dimulai: {payload}")
    try:
        while running:
            if not payload:
                break
            await client.send_message(BOT_USERNAME, payload)
            print(f"[{ts()}] [MASAK] {payload}")
            await asyncio.sleep(INTERVAL)
    except asyncio.CancelledError:
        pass
    finally:
        print(f"[{ts()}] Loop MASAK selesai.")

async def mancing_loop():
    global running, payload
    print(f"[{ts()}] Loop MANCING dimulai di lokasi: {payload}")
    try:
        while running:
            if not payload:
                break
            # kirim lokasi
            await client.send_message(BOT_USERNAME, payload)
            print(f"[{ts()}] [MANCING] Lokasi -> {payload}")

            try:
                # tunggu balasan bot
                resp = await client.wait_for(
                    events.NewMessage(from_users=BOT_USERNAME),
                    timeout=5
                )
            except asyncio.TimeoutError:
                print(f"[{ts()}] ⚠️ Tidak ada respon bot.")
                await asyncio.sleep(INTERVAL)
                continue

            # cek tombol Tarik Alat Pancing
            if resp.buttons:
                for row in resp.buttons:
                    for btn in row:
                        if "Tarik Alat Pancing" in btn.text:
                            await resp.click(btn)
                            print(f"[{ts()}] [MANCING] Klik 'Tarik Alat Pancing'")
                            break

            await asyncio.sleep(INTERVAL)
    except asyncio.CancelledError:
        pass
    finally:
        print(f"[{ts()}] Loop MANCING selesai.")

# ---------- HANDLERS ----------
@client.on(events.NewMessage(chats="me"))
async def handler_me(event):
    global mode, payload, running, task

    text = (event.raw_text or "").strip()
    if not text:
        return

    low = text.lower()

    # Command global
    if low == "stop":
        await stop_loop("⏹ Loop dihentikan.")
        return
    if low == "reset":
        await stop_loop("♻️ Reset selesai, kirim Masak/Mancing lagi.")
        return

    # Masuk mode masak
    if low == "masak":
        mode = "masak"
        payload = None
        await event.reply("🍳 Masak apa?")
        return

    # Masuk mode mancing
    if low == "mancing":
        mode = "mancing"
        payload = None
        await event.reply("🎣 Mancing dimana?")
        return

    # Jawaban payload masak
    if mode == "masak" and payload is None:
        payload = text
        running = True
        task = asyncio.create_task(masak_loop())
        await event.reply(f"▶️ Mulai MASAK: {payload} setiap {INTERVAL}s")
        return

    # Jawaban payload mancing
    if mode == "mancing" and payload is None:
        payload = text
        running = True
        task = asyncio.create_task(mancing_loop())
        await event.reply(f"▶️ Mulai MANCING di {payload} setiap {INTERVAL}s")
        return

@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def handler_bot(event):
    # Auto-stop jika energi habis
    if "tidak memiliki cukup energi" in (event.raw_text or "").lower():
        await stop_loop("🛑 Energi habis, loop dihentikan otomatis.")

# ---------- MAIN ----------
async def main():
    await client.start(phone=PHONE)
    print(f"[{ts()}] Client started. Listening Saved Messages...")

    instr = (
        "Bot siap ✅\n\n"
        "Command di Saved Messages:\n"
        "- Kirim 'Masak' → pilih payload masak\n"
        "- Kirim 'Mancing' → pilih lokasi mancing\n"
        "- 'stop' → hentikan loop\n"
        "- 'reset' → reset mode\n\n"
        f"Interval: {INTERVAL} detik"
    )
    await send_to_me(instr)
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[{ts()}] Exit by user.")
