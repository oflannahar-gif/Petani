# Petani.py — Auto Game Kampung Maifam (ENERGI UPGRADE)

import os
import asyncio
import random
import logging
import datetime

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
    "masak": {"aktif": False, "kode": None, "pause": False},
    "mancing": {"aktif": False, "lokasi": None, "pause": False},
    "grinding": {"aktif": False, "loops": 0, "count": 0, "pause": False},
    "macul": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180, "target": BOT_USERNAME, "pause": False},
    "macul_guild": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180, "pause": False},
    "macul_global": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180, "pause": False},
    "skygarden": {"aktif": False, "interval": 420, "pause": False},
    "ternakkhusus": {"aktif": False, "pause": False},
    "energi_habis": False
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

# =============== LOOPS ================
async def loop_ternakkhusus():
    data = state["ternakkhusus"]
    print(">> Loop Ternak Khusus dimulai")
    await safe_send("🐮 Auto Ternak Khusus dimulai", OWNER_ID)

    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)  # tunggu saat pause
        now = datetime.datetime.now()
        next_hour = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        wait_time = (next_hour - now).total_seconds()
        print(f"Menunggu {int(wait_time // 60)} menit hingga jam {next_hour.hour}:00")
        await asyncio.sleep(wait_time)

        if not data["aktif"]:
            break

        await safe_send("/beriMakanx")
        print(f"[SEND] /beriMakanx → berikutnya akan dikirim pukul {next_hour.hour + 1}:00")

    print(">> Loop Ternak Khusus berhenti")
    await safe_send("🐮 Auto Ternak Khusus dimatikan", OWNER_ID)

async def loop_skygarden():
    data = state["skygarden"]
    print(">> Loop Sky Garden dimulai")
    await safe_send("🌿 Auto Sky Garden dimulai", OWNER_ID)
    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        await safe_send("/sg_panen")
        await asyncio.sleep(data["interval"])
    print(">> Loop Sky Garden berhenti")

async def loop_masak():
    data = state["masak"]
    print(">> Loop Masak dimulai")
    while data["aktif"] and data["kode"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        await safe_send(data["kode"])
        await asyncio.sleep(2)
    print(">> Loop Masak berhenti")

async def loop_mancing():
    data = state["mancing"]
    print(f">> Loop Mancing dimulai di {data['lokasi']}")
    await safe_send(data["lokasi"])
    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        await asyncio.sleep(1)
    print(">> Loop Mancing berhenti")

async def loop_grinding():
    data = state["grinding"]
    print(f">> Loop Grinding dimulai ({data['loops']}x)")
    data["count"] = 0
    while data["aktif"] and data["count"] < data["loops"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
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
        while data.get("pause", False):
            await asyncio.sleep(5)
        if name == "macul_global":
            await safe_send(f"/tanam_{data['tanaman']}_{data['jumlah']}", GLOBAL_GROUP)
            await asyncio.sleep(durasi)
            await safe_send("/panen", GLOBAL_GROUP)
            await asyncio.sleep(305)
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
        if isinstance(v, dict) and "aktif" in v:
            v["aktif"] = False

# ================= OWNER CMD / HANDLER ================
@client.on(events.NewMessage(from_users=OWNER_ID))
async def cmd_owner(event):
    msg = (event.raw_text or "").strip()
    lmsg = msg.lower()
    print(f">> INPUT OWNER: {msg}")

    # === TERNAK KHUSUS ===
    if lmsg in ("tk on", "/tk on"):
        if not state["ternakkhusus"]["aktif"]:
            state["ternakkhusus"]["aktif"] = True
            await event.reply("🐮 Auto Ternak Khusus diaktifkan.")
            asyncio.create_task(loop_ternakkhusus())
        else:
            await event.reply("❗ Auto Ternak Khusus sudah aktif.")
        return

    if lmsg in ("tk off", "/tk off"):
        if state["ternakkhusus"]["aktif"]:
            state["ternakkhusus"]["aktif"] = False
            await event.reply("⏹ Auto Ternak Khusus dimatikan.")
        else:
            await event.reply("❗ Auto Ternak Khusus belum aktif.")
        return

    # === SKY GARDEN ===
    if lmsg in ("sg on", "/sg on"):
        state["skygarden"]["aktif"] = True
        await event.reply("🌿 Auto Sky Garden diaktifkan.")
        asyncio.create_task(loop_skygarden())
        return

    if lmsg in ("sg off", "/sg off"):
        state["skygarden"]["aktif"] = False
        await event.reply("⏹ Auto Sky Garden dimatikan.")
        return

    # === MASAK ===
    if lmsg == "masak":
        state["masak"].update({
            "aktif": False,
            "kode": None,
            "menunggu_input": True
        })
        await event.reply("🍳 Mau masak apa?")
        return
    if state["masak"].get("menunggu_input", False):
        state["masak"].update({
            "aktif": True, 
            "kode": msg,
            "menunggu_input": False
        })
        await event.reply(f"Mulai auto-masak: {msg}")
        asyncio.create_task(loop_masak())
        return

    # === MANCING ===
    if lmsg == "mancing":
        state["mancing"].update({"aktif": False, "lokasi": None})
        state["mancing"]["menunggu_input"] = True
        await event.reply("🎣 Mancing dimana?")
        return
    if state["mancing"].get("menunggu_input", False) and not state["mancing"]["aktif"]:
        if msg:
            state["mancing"].update({
                "aktif": True, 
                "lokasi": msg,
                "menunggu_input": False
            })
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

    # ENERGI HABIS → PAUSE SEMUA LOOP
    if "kamu tidak memiliki cukup energi" in text and "/tidur" in text:
        print("⚠️ Energi habis! Semua loop dipause sementara.")
        state["energi_habis"] = True
        for v in state.values():
            if isinstance(v, dict) and "pause" in v:
                v["pause"] = True
        await safe_send("/restore")
        return

    # ENERGI PULIH → RESUME SEMUA LOOP
    if "energi berhasil dipulihkan" in text:
        print("✅ Energi pulih, semua loop dilanjutkan.")
        state["energi_habis"] = False
        for v in state.values():
            if isinstance(v, dict) and "pause" in v:
                v["pause"] = False
        await safe_send("⚡ Semua loop dilanjutkan kembali.")
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
                 "- sg on / sg off (sky garden)\n"
                 "- tk on / tk off (ternak khusus)\n"
                 "- stop atau stop_[mode]")
    await safe_send(msg_intro, "me")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
