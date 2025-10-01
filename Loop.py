#!/usr/bin/env python3
# auto_mancing.py

import asyncio
import os
from telethon import TelegramClient, events
from dotenv import load_dotenv

# ---------- CONFIG ----------
load_dotenv("kunci.env")

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
BOT_USERNAME = os.getenv("BOT_USERNAME")   # username bot game
OWNER_ID = int(os.getenv("OWNER_ID"))      # ID kamu sendiri

SESSION = "loop_session"  # nama session file
# ----------------------------

client = TelegramClient(SESSION, API_ID, API_HASH)

# status
fishing = False
spot = None


@client.on(events.NewMessage(from_users=OWNER_ID))  # dengar perintah hanya dari kamu
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
            msg = await client.send_message(BOT_USERNAME, spot)

            # tunggu balasan dari bot
            resp = await client.wait_for(
                events.NewMessage(from_users=BOT_USERNAME),
                timeout=10
            )

            # klik tombol kalau ada
            if resp.buttons:
                await resp.click(0)  # klik tombol pertama ("Tarik Alat Pancing")

            await asyncio.sleep(2)  # delay sebelum ulang lagi

        except asyncio.TimeoutError:
            print("⚠️ Timeout: tidak ada balasan bot.")
        except Exception as e:
            print("❌ Error:", e)
            fishing = False


async def main():
    await client.start(phone=PHONE)
    print("✅ Bot siap, kirim nama lokasi di Saved Messages kamu untuk mulai mancing!")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())


