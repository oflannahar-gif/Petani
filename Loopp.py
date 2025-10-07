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

# auto_game_full.py — Auto Game Kampung Maifam
import os
import asyncio
import random
import logging
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# ---------------- CONFIG ----------------
load_dotenv("kunci.env")
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
PHONE = os.getenv("PHONE") or ""
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "KampungMaifamBot").lstrip('@')
OWNER_ID = int(os.getenv("OWNER_ID") or 0)
GLOBAL_GROUP = "@KampungMaifamGlobal"

if not API_ID or not API_HASH or not PHONE:
    raise SystemExit("ERROR: Pastikan API_ID, API_HASH, PHONE ter-set di kunci.env")

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger("auto_game_bot")

# ---------------- CLIENT ----------------
SESSION_STRING = os.getenv("TELEGRAM_SESSION")
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient("loop_session", API_ID, API_HASH)

# ---------------- QUEUE ----------------
message_queue = asyncio.Queue()

async def safe_send(msg, to=None):
    await message_queue.put((msg, to or BOT_USERNAME))

async def message_worker():
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

# ---------------- STATE ----------------
state = {
    "masak": {"aktif": False, "kode": None},
    "mancing": {"aktif": False, "lokasi": None},
    "grinding": {"aktif": False, "loops": 0, "count": 0},
    "macul": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180, "target": BOT_USERNAME},
    "macul_guild": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180},
    "macul_global": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180}
}

grinding_sequence = [
    "/tanamGuild_KacangTanah_6000",
    "/KebunGuild_Siram",
    "/kebunGuild_PanenSekarang"
]

tanaman_data = {}

# ---------------- LOAD TANAMAN ----------------
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
    print(f"🌿 {len(tanaman_data)} tanaman dimuat: {', '.join(tanaman_data.keys())}")

# ---------------- LOOPS ----------------
async def loop_masak():
    data = state["masak"]
    print(">> Loop Masak dimulai")
    while data["aktif"] and data["kode"]:
        await safe_send(data["kode"])
        await asyncio.sleep(2)
    print(">> Loop Masak berhenti")

async def loop_mancing():
    data = state["mancing"]
    print(f">> Loop Mancing dimulai di {data['lokasi']}")
    await safe_send(data["lokasi"])
    while data["aktif"]:
        await asyncio.sleep(1)
    print(">> Loop Mancing berhenti")

async def loop_grinding():
    data = state["grinding"]
    print(f">> Loop Grinding dimulai ({data['loops']}x)")
    data["count"] = 0
    while data["aktif"] and data["count"] < data["loops"]:
        for cmd in grinding_sequence:
            if not data["aktif"]:
                break
            await safe_send(cmd)
            await asyncio.sleep(2)
        data["count"] += 1
        print(f">> Grinding ke-{data['count']} selesai")
    data["aktif"] = False
    await safe_send(f"✅ Grinding selesai ({data['loops']}x siklus)", OWNER_ID)

async def loop_macul(name="macul"):
    data = state[name]
    durasi = data.get("durasi", 180)
    target = data.get("target", BOT_USERNAME)
    print(f">> Mulai {name}: {data['tanaman']} ({data['jumlah']} pohon, {durasi}s)")
    await safe_send(f"🌱 Mulai {name}: {data['tanaman']} ({data['jumlah']} pohon, {durasi}s)", OWNER_ID)
    while data["aktif"]:
        if name == "macul_global":
            await safe_send(f"/tanam_{data['tanaman']}_{data['jumlah']}", GLOBAL_GROUP)
            await asyncio.sleep(durasi)
            await safe_send("/panen", GLOBAL_GROUP)
        elif name in ("macul", "macul_guild"):
            cmd_tanam = f"/tanam_{data['tanaman']}_{data['jumlah']}" if name=="macul" else f"/tanamGuild_{data['tanaman']}_{data['jumlah']}"
            cmd_siram = "/siram" if name=="macul" else "/KebunGuild_Siram"
            cmd_panen = "/ambilPanen" if name=="macul" else "/kebunGuild_AmbilPanen"
            await safe_send(cmd_tanam, target)
            await asyncio.sleep(2)
            await safe_send(cmd_siram, target)
            await asyncio.sleep(durasi)
            await safe_send(cmd_panen, target)
        await asyncio.sleep(3)
    print(f">> Loop {name} berhenti")

# ---------------- STOP ALL ----------------
def stop_all():
    for v in state.values():
        v["aktif"] = False

# ---------------- OWNER CMD ----------------
@client.on(events.NewMessage(from_users=OWNER_ID))
async def cmd_owner(event):
    msg = (event.raw_text or "").strip()
    lmsg = msg.lower()
    print(f">> INPUT OWNER: {msg}")

    # === MASAK ===
    if lmsg == "masak":
        state["masak"].update({"aktif": False, "kode": None})
        await event.reply("🍳 Mau masak apa? (kirim kode seperti /masak_xxx)")
        return
    if lmsg.startswith("/masak_") and not state["masak"]["aktif"]:
        state["masak"].update({"aktif": True, "kode": msg})
        await event.reply(f"Mulai auto-masak: {msg}")
        asyncio.create_task(loop_masak())
        return

    # === MANCING ===
    if lmsg == "mancing":
        state["mancing"].update({"aktif": False, "lokasi": None})
        await event.reply("🎣 Mancing dimana?")
        return
    if state["mancing"]["lokasi"] is None and lmsg not in ("masak","grinding","macul","macul_guild","macul_global"):
        state["mancing"].update({"aktif": True, "lokasi": msg})
        await event.reply(f"Mulai auto-mancing di {msg} 🎣")
        asyncio.create_task(loop_mancing())
        return

    # === GRINDING ===
    if lmsg == "grinding":
        state["grinding"].update({"aktif": False, "loops": 0, "count": 0})
        await event.reply("🔁 Mau berapa kali grinding?")
        return
    if lmsg.isdigit() and state["grinding"]["loops"]==0:
        state["grinding"].update({"aktif": True, "loops": int(lmsg), "count":0})
        await event.reply(f"Mulai grinding sebanyak {lmsg}x siklus 🔄")
        asyncio.create_task(loop_grinding())
        return

    # === MACUL (PRIBADI / GUILD / GLOBAL) ===
    if lmsg in ("macul","macul_guild","macul_global"):
        load_tanaman()
        state[lmsg].update({"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180, "target": BOT_USERNAME})
        if lmsg=="macul_global":
            await event.reply(f"🌱 Mau tanam apa di Global? (macul_global <nama> <jumlah>)")
        else:
            await event.reply(f"🌱 Mau tanam apa di {lmsg.replace('_',' ')}? (macul/ macul_guild <nama> <jumlah>)")
        return

    # One-line format: macul <nama> <jumlah>
    for key in ["macul","macul_guild","macul_global"]:
        if lmsg.startswith(key+" ") or lmsg.startswith("/"+key+" "):
            parts = msg.replace("/","").split()
            if len(parts)>=3 and parts[1].strip() and parts[2].isdigit():
                tanaman = parts[1].strip().lower()
                jumlah = int(parts[2])
                durasi = tanaman_data.get(tanaman,180)
                state[key].update({"aktif": True,"tanaman":tanaman,"jumlah":jumlah,"durasi":durasi})
                if key!="macul_global":
                    target = BOT_USERNAME if key=="macul" else BOT_USERNAME
                    state[key]["target"] = target
                await event.reply(f"Mulai auto {key.replace('_',' ')} {parts[1]} ({jumlah} pohon, {durasi}s)")
                asyncio.create_task(loop_macul(key))
                return
            else:
                await event.reply(f"Format: {key} <nama> <jumlah>")
                return

    # === STOP ===
    if lmsg.startswith("stop"):
        if lmsg in ("stop","stop_all"):
            stop_all()
            await event.reply("⏹ Semua loop dihentikan.")
            return
        mode = lmsg.replace("stop_","")
        if mode in state and state[mode]["aktif"]:
            state[mode]["aktif"] = False
            await event.reply(f"⏹ Loop {mode} dihentikan.")
        else:
            await event.reply(f"❗ Tidak ada loop {mode} aktif / format salah")
        return
        
    print(f"❗ Perintah tidak dikenali: {msg}")


    

# ---------------- BOT HANDLER ----------------
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_reply(event):
    text = (event.raw_text or "").lower()
    print(f"[BOT] {text[:120]}...")
    # energi habis
    if "kamu tidak memiliki cukup energi" in text and "/tidur" in text:
        print("⚠️ Energi habis! Semua loop dihentikan.")
        stop_all()
        await safe_send("⚠️ Energi habis! Semua loop otomatis dihentikan.", OWNER_ID)
        return

    # MANCING
    s = state["mancing"]
    if s["aktif"]:
        if event.buttons:
            for row in event.buttons:
                for button in row:
                    if "Tarik Alat Pancing" in (button.text or ""):
                        await human_sleep()
                        await button.click()
                        print(">> Klik 'Tarik Alat Pancing'")
                        return
        if "kamu mendapatkan" in text:
            await human_sleep(2,3)
            await safe_send(s["lokasi"])
            print(f">> Kirim ulang lokasi: {s['lokasi']}")

# ---------------- MAIN ----------------
async def main():
    await client.start(phone=PHONE)
    logger.info("Client started")
    load_tanaman()
    asyncio.create_task(message_worker())
    msg_intro = ("Bot siap ✅\n\nCommand:\n"
                 "- masak → lalu kirim kode masak (/masak_xxx)\n"
                 "- mancing → lalu kirim lokasi\n"
                 "- grinding → lalu kirim jumlah loop\n"
                 "- macul <tanaman> <jumlah>\n"
                 "- macul_guild <tanaman> <jumlah>\n"
                 "- macul_global <tanaman> <jumlah>\n"
                 "- stop atau stop_[mode]")
    await safe_send(msg_intro, "me")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
