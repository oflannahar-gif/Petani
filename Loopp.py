# auto_game.py — Auto Mancing, Masak, Macul & Grinding di Kampung Maifam
# Versi: perbaikan durasi macul (case-insensitive) + load_tanaman dipanggil di startup
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
    """Masukkan pesan ke queue"""
    await message_queue.put((msg, to or BOT_USERNAME))

async def message_worker():
    """Kirim pesan satu per satu dengan delay aman"""
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

# ---------------- GLOBAL STATE ----------------
state = {
    "masak": {"aktif": False, "kode": None},
    "mancing": {"aktif": False, "lokasi": None},
    "grinding": {"aktif": False, "loops": 0, "count": 0},
    "macul": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180}
}

grinding_sequence = [
    "/tanamGuild_KacangTanah_6000",
    "/KebunGuild_Siram",
    "/kebunGuild_PanenSekarang"
]

tanaman_data = {}  # akan berisi {'kentang': 245, ...} (kunci lowercase)

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

# ---------------- LOOP MASAK ----------------
async def loop_masak():
    data = state["masak"]
    print(">> Loop Masak dimulai")
    while data["aktif"] and data["kode"]:
        await safe_send(data["kode"])
        await asyncio.sleep(2)
    print(">> Loop Masak berhenti")

# ---------------- LOOP MANCING ----------------
async def loop_mancing():
    data = state["mancing"]
    print(f">> Loop Mancing dimulai di {data['lokasi']}")
    # Kirim lokasi pertama lewat queue (safe_send) supaya tidak langsung tabrakan
    await safe_send(data["lokasi"])
    while data["aktif"]:
        await asyncio.sleep(1)
    print(">> Loop Mancing berhenti")

# ---------------- LOOP GRINDING ----------------
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

# ---------------- LOOP MACUL ----------------
async def loop_macul():
    data = state["macul"]
    durasi = data.get("durasi", 180)
    print(f">> Mulai auto macul: {data['tanaman']} ({data['jumlah']} pohon, {durasi}s)")
    await safe_send(f"🌱 Mulai auto Macul: {data['tanaman']} ({data['jumlah']} pohon, {durasi}s)", OWNER_ID)

    while data["aktif"]:
        await safe_send(f"/tanam_{data['tanaman']}_{data['jumlah']}")
        await asyncio.sleep(2)
        await safe_send("/siram")
        await asyncio.sleep(durasi)
        await safe_send("/ambilPanen")
        await asyncio.sleep(3)
    print(">> Loop Macul berhenti")

# ---------------- STOP SEMUA LOOP ----------------
def stop_all():
    for v in state.values():
        v["aktif"] = False

# ---------------- OWNER COMMAND ----------------
@client.on(events.NewMessage(from_users=OWNER_ID))
async def cmd_owner(event):
    msg = (event.raw_text or "").strip()
    lmsg = msg.lower()
    print(f">> INPUT OWNER: {msg}")

    # === MASAK flow (two-step or one-line) ===
    if lmsg == "masak":
        state["masak"].update({"aktif": False, "kode": None})
        await event.reply("🍳 Mau masak apa? (kirim kode seperti /masak_xxx atau /masak_nama_jumlah)")
        return
    if lmsg.startswith("/masak_") and not state["masak"]["aktif"]:
        state["masak"].update({"aktif": True, "kode": msg})
        await event.reply(f"Mulai auto-masak: {msg}")
        asyncio.create_task(loop_masak())
        return

    # === MANCING flow ===
    if lmsg == "mancing":
        state["mancing"].update({"aktif": False, "lokasi": None})
        await event.reply("🎣 Mancing dimana?")
        return
    # jika sudah beri lokasi (tidak dimulai dengan '/')
    if not lmsg.startswith("/") and state["mancing"]["lokasi"] is None and lmsg not in ("masak","grinding","macul"):
        state["mancing"].update({"aktif": True, "lokasi": msg})
        await event.reply(f"Mulai auto-mancing di {msg} 🎣")
        asyncio.create_task(loop_mancing())
        return

    # === GRINDING flow ===
    if lmsg == "grinding":
        state["grinding"].update({"aktif": False, "loops": 0, "count": 0})
        await event.reply("🔁 Mau berapa kali grinding?")
        return
    if lmsg.isdigit() and state["grinding"]["loops"] == 0:
        state["grinding"].update({"aktif": True, "loops": int(lmsg), "count": 0})
        await event.reply(f"Mulai grinding sebanyak {lmsg}x siklus 🔄")
        asyncio.create_task(loop_grinding())
        return

    # === MACUL flow: support both `macul` (two-step) and `macul <tanaman> <jumlah>` (one-line) ===
    if lmsg == "macul":
        load_tanaman()  # pastikan data terbaru
        state["macul"].update({"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180})
        await event.reply("🌱 Mau tanam apa? (kirim: macul <nama> <jumlah> atau mulai dengan 'macul' lalu kirim nama & jumlah)")
        return

    # one-line macul: "macul kentang 500" atau "/macul kentang 500"
    if lmsg.startswith("macul ") or lmsg.startswith("/macul "):
        parts = msg.split()
        if len(parts) >= 3 and parts[1].strip() and parts[2].isdigit():
            tanaman = parts[1].strip().lower()
            jumlah = int(parts[2])
            durasi = tanaman_data.get(tanaman, 180)
            state["macul"].update({"aktif": True, "tanaman": tanaman, "jumlah": jumlah, "durasi": durasi})
            await event.reply(f"Mulai auto Macul {parts[1].strip()} ({jumlah} pohon, {durasi}s)")
            asyncio.create_task(loop_macul())
            return
        else:
            await event.reply("Format macul: macul <tanaman> <jumlah>")
            return

    # two-step macul: after "macul" prompt, user sends name
    if state["macul"]["tanaman"] is None and lmsg in tanaman_data:
        # user sent plant name after being prompted
        tanaman = lmsg
        state["macul"]["tanaman"] = tanaman
        await event.reply(f"Berapa jumlah {tanaman} yang mau ditanam?")
        return
    # two-step quantity
    if state["macul"]["tanaman"] and state["macul"]["jumlah"] == 0 and lmsg.isdigit():
        jumlah = int(lmsg)
        tanaman = state["macul"]["tanaman"]
        durasi = tanaman_data.get(tanaman, 180)
        state["macul"].update({"aktif": True, "jumlah": jumlah, "durasi": durasi})
        await event.reply(f"Mulai Macul otomatis {tanaman} ({jumlah} pohon, {durasi}s).")
        asyncio.create_task(loop_macul())
        return

    # === STOP commands ===
    if lmsg.startswith("stop"):
        if lmsg == "stop" or lmsg == "stop_all":
            stop_all()
            await event.reply("⏹ Semua loop dihentikan.")
            return
        # stop per-mode: stop_masak, stop_mancing, stop_grinding, stop_macul
        mode = lmsg.replace("stop_", "")
        if mode in state and state[mode]["aktif"]:
            state[mode]["aktif"] = False
            await event.reply(f"⏹ Loop {mode} dihentikan.")
        else:
            await event.reply(f"❗ Tidak ada loop {mode} yang aktif atau format stop salah.")
        return

    # fallback: unrecognized input
    await event.reply("❗ Perintah tidak dikenali. Gunakan: masak / mancing / grinding / macul / stop")

# ---------------- BOT HANDLER ----------------
@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_reply(event):
    text = (event.raw_text or "").lower()
    print(f"[BOT] {text[:120]}...")

    # Energi habis -> hentikan semua loop
    if "kamu tidak memiliki cukup energi" in text and "/tidur" in text:
        print("⚠️ Energi habis! Semua loop dihentikan.")
        stop_all()
        await safe_send("⚠️ Energi habis! Semua loop otomatis dihentikan.", OWNER_ID)
        return

    # MANCING: klik tombol + kirim ulang lokasi setelah "kamu mendapatkan"
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
            await human_sleep(2, 3)
            await safe_send(s["lokasi"])
            print(f">> Kirim ulang lokasi: {s['lokasi']}")

# ---------------- MAIN ----------------
async def main():
    await client.start(phone=PHONE)
    logger.info("Client started")
    # load tanaman saat startup
    load_tanaman()

    asyncio.create_task(message_worker())
    msg_intro = ("Bot siap ✅\n\nCommand:\n"
                 "- masak → lalu kirim kode masak (/masak_xxx)\n"
                 "- mancing → lalu kirim lokasi\n"
                 "- grinding → lalu kirim jumlah loop\n"
                 "- macul <tanaman> <jumlah>   (atau: ketik 'macul' lalu kirim nama & jumlah)\n"
                 "- stop atau stop_[mode]")
    await safe_send(msg_intro, "me")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
