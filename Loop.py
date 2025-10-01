#!/usr/bin/env python3
# Loop.py — Auto Mancing Telethon

import asyncio
import os
from telethon import TelegramClient, events
from dotenv import load_dotenv

# ---------- CONFIG ----------
load_dotenv("kunci.env")

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
BOT_USERNAME = os.getenv("BOT_USERNAME")   # username bot game, ex: "KampungMaifamBot"
OWNER_ID = int(os.getenv("OWNER_ID"))      # ID kamu sendiri (biar hanya kamu yang bisa kontrol)

SESSION = "loop_session"  # nama file session
# ----------------------------

client = TelegramClient(SESSION, API_ID, API_HASH)

# status global
fishing = False
spot = None


@client.on(events.NewMessage(from_users=OWNER_ID))  # hanya dengar pesan dari kamu
async def command_handler(event):
    global fishing, spot

    cmd = event.raw_text.strip()

    if cmd.lower() == "stop":
        fishing = False
        await event.respond("⛔ Auto mancing dihentikan.")
        return

    # anggap selain 'stop' = nama spot
    spot = cmd
    fishing = True
    await event.respond(f"🎣 Mulai auto mancing di **{spot}**")
    asyncio.create_task(loop_mancing())


async def loop_mancing():
    global fishing, spot
    while fishing:
        try:
            # kirim lokasi ke bot game
            await client.send_message(BOT_USERNAME, spot)

            # tunggu balasan bot (max 10 detik)
            try:
                resp = await asyncio.wait_for(
                    client.wait_event(events.NewMessage(from_users=BOT_USERNAME)),
                    timeout=10
                )
            except asyncio.TimeoutError:
                print("⚠️ Timeout: tidak ada balasan bot.")
                continue

            # klik tombol kalau ada
            if resp.buttons:
                try:
                    await resp.click(0)  # klik tombol pertama ("Tarik Alat Pancing")
                except Exception as e:
                    print("⚠️ Gagal klik tombol:", e)

            # delay sebelum ulang lagi
            await asyncio.sleep(2)

        except Exception as e:
            print("❌ Error:", e)
            fishing = False


async def main():
    await client.start(phone=PHONE)
    print("✅ Bot siap, kirim nama lokasi di Saved Messages kamu untuk mulai mancing!")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
