# auto_game_full.py — Auto Mancing, Masak, Macul (pribadi + guild) & Grinding di Kampung Maifam
# Features:
#   - 'Masak' → loop kirim kode masak tiap 2 detik
#   - 'Mancing' → loop kirim lokasi + klik "Tarik Alat Pancing"
#   - 'Grinding' → kirim urutan tanam-siram-panen berulang sesuai jumlah input
#   - 'Macul' (pribadi) → /tanam_<tanaman>_<jumlah>, /siram, /ambilPanen
#   - 'Macul Guild' → /tanamGuild_<tanaman>_<jumlah>, /KebunGuild_Siram, /kebunGuild_AmbilPanen
#   - Multi-loop paralel, per-mode stop (stop_[mode]) and global stop
#   - Auto-stop jika energi habis
#
# Requirements:
#   pip install telethon python-dotenv

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
    """Masukkan pesan ke queue (dest default = BOT_USERNAME)."""
    await message_queue.put((msg, to or BOT_USERNAME))

async def message_worker():
    """Kirim pesan satu per satu dengan delay aman."""
    while True:
        msg, dest = await message_queue.get()
        try:
            await client.send_message(dest, msg)
            print(f"[SEND] → {dest}: {msg}")
        except Exception as e:
            print(f"[!] Gagal kirim {msg} ke {dest}: {e}")
        # jeda aman antar pesan supaya tidak bentrok / rate limit
        await asyncio.sleep(2)

async def human_sleep(min_s=1.0, max_s=1.5):
    await asyncio.sleep(random.uniform(min_s, max_s))

# ---------------- GLOBAL STATE (per-mode) ----------------
state = {
    "masak": {"aktif": False, "kode": None},
    "mancing": {"aktif": False, "lokasi": None},
    "grinding": {"aktif": False, "loops": 0, "count": 0},
    "macul": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180},
    "macul_guild": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180}
}

# urutan grinding (tetap pake contoh)
grinding_sequence = [
    "/tanamGuild_KacangTanah_6000",
    "/KebunGuild_Siram",
    "/kebunGuild_PanenSekarang"
]

# tanaman data (kunci: lowercase)
tanaman_data = {}

# ---------------- load tanaman.txt (normalized keys) ----------------
def load_tanaman():
    tanaman_data.clear()
    if not os.path.exists("tanaman.txt"):
        print("⚠️ File tanaman.txt tidak ditemukan.")
        return
    with open("tanaman.txt", "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                nama, waktu = line.split("=", 1)
                nama_k = nama.strip().lower()
                try:
                    tanaman_data[nama_k] = int(waktu.strip())
                except ValueError:
                    print(f"⚠️ Baris tanaman tidak valid dilewati: {line}")
                    continue
    print(f"🌿 {len(tanaman_data)} tanaman dimuat: {', '.join(tanaman_data.keys())}")

# ---------------- helper: stop all / stop specific ----------------
def stop_all():
    for v in state.values():
        v["aktif"] = False

# ---------------- LOOP MASAK ----------------
async def loop_masak():
    d = state["masak"]
    print(">> Loop Masak dimulai")
    while d["aktif"] and d["kode"]:
        await safe_send(d["kode"])
        await asyncio.sleep(2)
    print(">> Loop Masak berhenti")

# ---------------- LOOP MANCING ----------------
async def loop_mancing():
    d = state["mancing"]
    print(f">> Loop Mancing dimulai di {d['lokasi']}")
    # Kirim lokasi pertama lewat queue (safe_send)
    await safe_send(d["lokasi"])
    # loop inti: actual send dan klik di handler bot_reply (respon)
    while d["aktif"]:
        await asyncio.sleep(1)
    print(">> Loop Mancing berhenti")

# ---------------- LOOP GRINDING ----------------
async def loop_grinding():
    d = state["grinding"]
    print(f">> Loop Grinding dimulai ({d['loops']}x)")
    d["count"] = 0
    while d["aktif"] and d["count"] < d["loops"]:
        for cmd in grinding_sequence:
            if not d["aktif"]:
                break
            await safe_send(cmd)
            await asyncio.sleep(2)
        d["count"] += 1
        print(f">> Grinding ke-{d['count']} selesai")
    d["aktif"] = False
    await safe_send(f"✅ Grinding selesai ({d['loops']}x siklus)", OWNER_ID)

# ---------------- LOOP MACUL (PRIBADI) ----------------
async def loop_macul():
    d = state["macul"]
    durasi = d.get("durasi", 180)
    print(f">> Mulai auto macul (pribadi): {d['tanaman']} ({d['jumlah']} pohon, {durasi}s)")
    await safe_send(f"🌱 Mulai auto Macul (pribadi): {d['tanaman']} ({d['jumlah']} pohon, {durasi}s)", OWNER_ID)

    while d["aktif"]:
        await safe_send(f"/tanam_{d['tanaman']}_{d['jumlah']}")
        await asyncio.sleep(2)
        await safe_send("/siram")
        await asyncio.sleep(durasi)
        await safe_send("/ambilPanen")
        await asyncio.sleep(3)
    print(">> Loop Macul (pribadi) berhenti")

# ---------------- LOOP MACUL GUILD ----------------
async def loop_macul_guild():
    d = state["macul_guild"]
    durasi = d.get("durasi", 180)
    print(f">> Mulai auto macul (Guild): {d['tanaman']} ({d['jumlah']} pohon, {durasi}s)")
    await safe_send(f"🛡️ Mulai auto Macul (Guild): {d['tanaman']} ({d['jumlah']} pohon, {durasi}s)", OWNER_ID)

    while d["aktif"]:
        await safe_send(f"/tanamGuild_{d['tanaman']}_{d['jumlah']}")
        await asyncio.sleep(2)
        await safe_send("/KebunGuild_Siram")
        await asyncio.sleep(durasi)
        await safe_send("/kebunGuild_AmbilPanen")
        await asyncio.sleep(3)
    print(">> Loop Macul (Guild) berhenti")

# ---------------- OWNER COMMAND HANDLER ----------------
@client.on(events.NewMessage(from_users=OWNER_ID))
async def cmd_owner(event):
    msg = (event.raw_text or "").strip()
    lmsg = msg.lower()
    print(f">> INPUT OWNER: {msg}")

    # --- MASAK ---
    if lmsg == "masak":
        state["masak"].update({"aktif": False, "kode": None})
        await event.reply("🍳 Mau masak apa? (kirim kode seperti /masak_xxx)")
        return
    if lmsg.startswith("/masak_") and not state["masak"]["aktif"]:
        state["masak"].update({"aktif": True, "kode": msg})
        await event.reply(f"Mulai auto-masak: {msg}")
        asyncio.create_task(loop_masak())
        return

    # --- MANCING ---
    if lmsg == "mancing":
        state["mancing"].update({"aktif": False, "lokasi": None})
        await event.reply("🎣 Mancing dimana?")
        return
    if (not lmsg.startswith("/")) and state["mancing"]["lokasi"] is None and lmsg not in ("masak", "grinding", "macul", "macul_guild"):
        state["mancing"].update({"aktif": True, "lokasi": msg})
        await event.reply(f"Mulai auto-mancing di {msg} 🎣")
        asyncio.create_task(loop_mancing())
        return

    # --- GRINDING ---
    if lmsg == "grinding":
        state["grinding"].update({"aktif": False, "loops": 0, "count": 0})
        await event.reply("🔁 Mau berapa kali grinding?")
        return
    if lmsg.isdigit() and state["grinding"]["loops"] == 0:
        state["grinding"].update({"aktif": True, "loops": int(lmsg), "count": 0})
        await event.reply(f"Mulai grinding sebanyak {lmsg}x siklus 🔄")
        asyncio.create_task(loop_grinding())
        return

    # --- MACUL (one-line and two-step supported) ---
    if lmsg == "macul":
        load_tanaman()
        state["macul"].update({"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180})
        await event.reply("🌱 Mau tanam apa? (kirim: macul <nama> <jumlah>)")
        return

    if lmsg.startswith("macul ") or lmsg.startswith("/macul "):
        parts = msg.split()
        if len(parts) >= 3 and parts[1].strip() and parts[2].isdigit():
            tanaman = parts[1].strip().lower()
            jumlah = int(parts[2])
            durasi = tanaman_data.get(tanaman, 180)
            state["macul"].update({"aktif": True, "tanaman": tanaman, "jumlah": jumlah, "durasi": durasi})
            await event.reply(f"Mulai auto Macul (pribadi) {parts[1].strip()} ({jumlah} pohon, {durasi}s)")
            asyncio.create_task(loop_macul())
            return
        else:
            await event.reply("Format macul: macul <tanaman> <jumlah>")
            return

    # two-step macul (after prompt)
    if state["macul"]["tanaman"] is None and lmsg in tanaman_data:
        state["macul"]["tanaman"] = lmsg
        await event.reply(f"Berapa jumlah {lmsg} yang mau ditanam?")
        return
    if state["macul"]["tanaman"] and state["macul"]["jumlah"] == 0 and lmsg.isdigit():
        jumlah = int(lmsg)
        tanaman = state["macul"]["tanaman"]
        durasi = tanaman_data.get(tanaman, 180)
        state["macul"].update({"aktif": True, "jumlah": jumlah, "durasi": durasi})
        await event.reply(f"Mulai Macul otomatis {tanaman} ({jumlah} pohon, {durasi}s).")
        asyncio.create_task(loop_macul())
        return

    # --- MACUL GUILD (one-line) ---
    # command format: macul_guild <tanaman> <jumlah>
    if lmsg.startswith("macul_guild ") or lmsg.startswith("maculguild ") or lmsg.startswith("/macul_guild "):
        # support several input variants
        parts = msg.replace("/","").split()
        # find the command token e.g. "macul_guild" or "maculguild"
        if len(parts) >= 3:
            # tanaman key normalized to lowercase
            tanaman = parts[1].strip().lower()
            jumlah_s = parts[2].strip()
            if not jumlah_s.isdigit():
                await event.reply("Format macul_guild: macul_guild <tanaman> <jumlah>")
                return
            jumlah = int(jumlah_s)
            durasi = tanaman_data.get(tanaman, 180)
            state["macul_guild"].update({"aktif": True, "tanaman": tanaman, "jumlah": jumlah, "durasi": durasi})
            await event.reply(f"🛡️ Mulai auto Macul Guild {parts[1].strip()} ({jumlah} pohon, {durasi}s)")
            asyncio.create_task(loop_macul_guild())
            return
        await event.reply("Format macul_guild: macul_guild <tanaman> <jumlah>")
        return

    # --- STOP commands (global or per-mode) ---
    if lmsg.startswith("stop"):
        # stop all
        if lmsg == "stop" or lmsg == "stop_all":
            stop_all()
            await event.reply("⏹ Semua loop dihentikan.")
            return
        # stop per-mode: stop_masak, stop_mancing, stop_grinding, stop_macul, stop_macul_guild
        mode_cmd = lmsg.replace("stop_", "")
        if mode_cmd in state:
            state[mode_cmd]["aktif"] = False
            await event.reply(f"⏹ Loop {mode_cmd} dihentikan.")
        else:
            await event.reply(f"❗ Tidak ada loop '{mode_cmd}' yang aktif atau format stop salah.")
        return

    # fallback: unrecognized
    await event.reply("❗ Perintah tidak dikenali. Gunakan: masak / mancing / grinding / macul / macul_guild / stop")

# ---------------- BOT GAME HANDLER ----------------
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_reply(event):
    text = (event.raw_text or "").lower()
    print(f"[BOT] {text[:140]}...")

    # Energi habis -> hentikan semua loop
    if "kamu tidak memiliki cukup energi" in text and "/tidur" in text:
        print("⚠️ Energi habis! Semua loop dihentikan.")
        stop_all()
        await safe_send("⚠️ Energi habis! Semua loop otomatis dihentikan.", OWNER_ID)
        return

    # MANCING: klik tombol "Tarik Alat Pancing" jika ada, dan kirim ulang lokasi setelah "kamu mendapatkan"
    s = state["mancing"]
    if s["aktif"]:
        if event.buttons:
            for row in event.buttons:
                for button in row:
                    if "Tarik Alat Pancing" in (button.text or ""):
                        await human_sleep()
                        try:
                            await button.click()
                            print(">> Klik 'Tarik Alat Pancing'")
                        except Exception as e:
                            print("❌ Gagal klik tombol pancing:", e)
                        return
        if "kamu mendapatkan" in text:
            # setelah dapat, tunggu sebentar lalu minta lokasi lagi
            await human_sleep(2, 3)
            await safe_send(s["lokasi"])
            print(f">> Kirim ulang lokasi: {s['lokasi']}")

# ---------------- MAIN ----------------
async def main():
    await client.start(phone=PHONE)
    logger.info("Client started")
    # load tanaman saat startup
    load_tanaman()

    # start queue worker
    asyncio.create_task(message_worker())

    msg_intro = ("Bot siap ✅\n\nCommand:\n"
                 "- masak → lalu kirim kode masak (/masak_xxx)\n"
                 "- mancing → lalu kirim lokasi\n"
                 "- grinding → lalu kirim jumlah loop\n"
                 "- macul <tanaman> <jumlah>\n"
                 "- macul_guild <tanaman> <jumlah>\n"
                 "- stop atau stop_[mode]")
    await safe_send(msg_intro, "me")
    print(msg_intro)

    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
