# Petani.py

import os
import asyncio
import random
import logging
import datetime
import re
import time

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from datetime import datetime

# ---------------- CONFIG ----------------
load_dotenv("kunci.env")
API_ID = int(os.getenv("API_ID") or 0)
API_HASH = os.getenv("API_HASH") or ""
PHONE = os.getenv("PHONE") or ""
BOT_USERNAME = (os.getenv("BOT_USERNAME") or "KampungMaifamBot").lstrip('@')
BOT_X = (os.getenv("BOT_X") or "KampungMaifamXBot").lstrip('@')
BOT_X4 = (os.getenv("BOT_X4") or "KampungMaifamX4Bot").lstrip('@')
GROUP_DANAU = "@danaudalamhutan"
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

PRIVATE_LOG_CHAT = "@CmdPetani"  # ID grup privat kamu

# === SAFE SEND Bot Alpha ===
async def safe_send(msg, to=None):
    if to == "me":
        to = PRIVATE_LOG_CHAT
    await message_queue.put((msg, to or BOT_USERNAME))

# === SAFE SEND Bot X ===
async def safe_send_x(msg, to=None):
    if to == "me":
        to = PRIVATE_LOG_CHAT
    await message_queue.put((msg, to or BOT_X))

# === SAFE SEND Bot X4 ===
async def safe_send_x4(msg, to=None):
    if to == "me":
        to = PRIVATE_LOG_CHAT
    await message_queue.put((msg, to or BOT_X4))

# === SAFE SEND Grup Danau ===
async def safe_send_d(msg, to=None):
    if to == "me":
        to = PRIVATE_LOG_CHAT
    await message_queue.put((msg, to or GROUP_DANAU))


# === SAFE SEND CEPAT (langsung kirim tanpa antre) ===
async def safe_send_cepat(msg, to=None):
    if to == "me":
        to = PRIVATE_LOG_CHAT
    dest = to or BOT_USERNAME
    try:
        await client.send_message(dest, msg)
        print(f"[RESTORE] → {dest}: {msg}")
    except Exception as e:
        print(f"[!] Gagal kirim cepat {msg} ke {dest}: {e}")


async def message_worker():
    while True:
        msg, dest = await message_queue.get()
        try:
            await client.send_message(dest, msg)
            print(f"{waktu()} [SEND] → {dest}: {msg}")
        except Exception as e:
            print(f"[!] Gagal kirim {msg} ke {dest}: {e}")
        await asyncio.sleep(2)

async def human_sleep(min_s=1.0, max_s=1.5):
    await asyncio.sleep(random.uniform(min_s, max_s))

# ---------------- STATE ----------------
state = {
    "masak": {"aktif": False, "kode": None, "loops": 0, "count": 0, "pause": False, "menunggu_input": False},
    "masak_x": {"aktif": False, "kode": None, "loops": 0, "count": 0, "pause": False, "menunggu_input": False},
    "mancing": {"aktif": False, "lokasi": None, "pause": False},
    "mancing_x": {"aktif": False, "lokasi": None, "pause": False},
    "macul": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180, "target": BOT_USERNAME, "pause": False},
    "macul_guild": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180, "pause": False},
    "macul_global": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180, "pause": False},
    "skygarden": {"aktif": False, "interval": 120, "pause": False},
    "sg_merge": {"aktif": False},
    "cb": {"aktif": False},
    "sg_upgrade": {"aktif": False},
    "fishing": {"aktif": False, "interval": 270, "pause": False},
    "maling": {"aktif": False, "interval": 615, "pause": False},
    "ternak": {"aktif": False, "interval": 910, "pause": False},
    "ternakkhusus": {"aktif": False, "pause": False},
    "animalhouse": {"aktif": False, "interval": 610, "pause": False},
    "greenhouse": {"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180, "pause": False},
    "energi_habis": False
}


tanaman_data = {}

# ---------------- LOAD DATA TANAMAN ----------------
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

# ---------------- LOAD DATA MALING ----------------
def load_maling():
    if not os.path.exists("Donasi.txt"):
        print("⚠️ File maling.txt tidak ditemukan.")
        return []
    lokasi_maling = []
    with open("Donasi.txt", "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if line and not line.startswith("#"):
                lokasi_maling.append(line)
    print(f"🦹‍♂️ {len(lokasi_maling)} lokasi maling dimuat.")
    return lokasi_maling




# =============== LOOPS ================

# === LOOP MALING ===
async def loop_maling():
    data = state["maling"]
    lokasi_list = load_maling()
    if not lokasi_list:
        print("⚠️ Tidak ada lokasi maling, loop maling dibatalkan.")
        return
    print(">> Loop Maling dimulai")
    await client.send_message(PRIVATE_LOG_CHAT, "🦹‍♂️ Auto Maling dimulai")
    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        if "index" not in data:
            data["index"] = 0

        lokasi = lokasi_list[data["index"]]
        data["index"] = (data["index"] + 1) % len(lokasi_list)

        await safe_send_x(f"{lokasi}")
        print(f"{waktu()} [SEND] maling {lokasi}")
        await asyncio.sleep(data["interval"])
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    print(">> Loop Maling berhenti")
    await client.send_message(PRIVATE_LOG_CHAT, "🦹‍♂️ Auto Maling dimatikan")

# === LOOP TERNAK KHUSUS ===
async def loop_ternakkhusus():
    data = state["ternakkhusus"]
    print(">> Loop Ternak Khusus dimulai")
    await client.send_message(PRIVATE_LOG_CHAT, "🐮 Auto Ternak Khusus dimulai")

    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        await asyncio.sleep(2)
        await safe_send_x4("/pelihara_AnakArwana_85")
        await asyncio.sleep(2)
        await safe_send_x4("/ambilHewan")
        await asyncio.sleep(2)
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    
    print(">> Loop Ternak Khusus berhenti")
    await client.send_message(PRIVATE_LOG_CHAT, "🐮 Auto Ternak Khusus dimatikan")

# === LOOP GRUP DANAU ===
async def loop_grup_danau():
    data = state["fishing"]
    print(">> Loop Grup Danau dimulai")
    await client.send_message(PRIVATE_LOG_CHAT, "🎣 Auto Mancing Grup Danau dimulai")
    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        await safe_send_d("/fish")
        await asyncio.sleep(data["interval"])
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    print(">> Loop Grup Danau berhenti")
    await client.send_message(PRIVATE_LOG_CHAT, "🎣 Auto Mancing Grup Danau berhenti.")

# === LOOP ANIMAL HOUSE ===
async def loop_animalhouse():
    data = state["animalhouse"]
    print(">> Loop Animal House dimulai")
    await client.send_message(PRIVATE_LOG_CHAT, "🏠 Auto Animal House dimulai")
    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        await asyncio.sleep(2)
        await safe_send("/ah_1_AmbilHasil")
        await asyncio.sleep(data["interval"])
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    print(">> Loop Animal House berhenti")
    await client.send_message(PRIVATE_LOG_CHAT, "🏠 Auto Animal House dimatikan")

# === LOOP SKY GARDEN ===
async def loop_skygarden():
    data = state["skygarden"]
    print(">> Loop Sky Garden dimulai")
    await client.send_message(PRIVATE_LOG_CHAT, "🌿 Auto Sky Garden dimulai")
    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        await safe_send("/sg_panen")
        await asyncio.sleep(data["interval"])
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    print(">> Loop Sky Garden berhenti")
    await client.send_message(PRIVATE_LOG_CHAT, "🌿 Auto Sky Garden dimatikan")

# === LOOP SG UPGRADE ===
async def loop_sg_upgrade():
    data = state["sg_upgrade"]
    print(">> Loop SG Upgrade dimulai")
    await client.send_message(PRIVATE_LOG_CHAT, "🚀 Auto SG Upgrade dimulai")
    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        await safe_send_x("/sg_upgrade", BOT_X)
        await asyncio.sleep(10)  # tunggu 5 menit sebelum upgrade lagi
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    print(">> Loop SG Upgrade berhenti")
    await client.send_message(PRIVATE_LOG_CHAT, "🚀 Auto SG Upgrade dimatikan")

# === LOOP SG MERGE ===
async def tunggu_balasan(bot_username, timeout=10):
    """
    Menunggu pesan baru dari bot dalam X detik.
    """
    start = time.time()

    last_id = None
    # Ambil ID terbaru dulu
    msg = await client.get_messages(bot_username, limit=1)
    if msg:
        last_id = msg[0].id

    while True:
        await asyncio.sleep(0.5)
        msg = await client.get_messages(bot_username, limit=1)
        if msg:
            if msg[0].id != last_id:
                return msg[0]  # ada pesan baru

        if time.time() - start > timeout:
            return None

sg_merge_running = False

# LEVEL FILTER — versi robust: deteksi dari huruf kapital akhir (SS atau 1 huruf)
LEVEL_ORDER = ["BIASA", "E", "D", "C", "B", "A", "S", "SS"]
VALID_SINGLE = {"E", "D", "C", "B", "A", "S"}

def ambil_level(nama: str) -> str:
    """
    Deteksi level dari nama buah dalam format seperti:
      - Mentimun      -> BIASA
      - MentimunE     -> E
      - MentimunD     -> D
      - WortelSS      -> SS
      - NanasKeramatB -> B
    Aturan: level ditandai oleh huruf kapital di akhir (atau 'SS').
    """
    if len(nama) >= 2 and nama.endswith("SS"):
        return "SS"

    last = nama[-1] if nama else ""
    if last.isupper() and last in VALID_SINGLE:
        return last

    return "BIASA"

def boleh_merge(cmd: str) -> bool:
    # ambil nama setelah prefix sekali
    nama = cmd.replace("/sg_merge_", "", 1)
    level = ambil_level(nama)
    # hanya boleh merge level BIASA, E, D
    return LEVEL_ORDER.index(level) <= LEVEL_ORDER.index("D")

# WAKTU (logging)
def waktu():
    return datetime.now().strftime("[%H:%M:%S]")

# LOOP SG MERGE 
async def loop_sg_merge(client, BOT_X, state):
    global sg_merge_running

    if sg_merge_running:
        print(f"{waktu()} ⚠️ Loop SG Merge sudah berjalan, abaikan panggilan baru.")
        return

    sg_merge_running = True
    print(f"{waktu()} 🌿 Auto SG Merge dimulai (setiap 1/2 jam).")

    # penanda apakah SGM pernah nge-pause mancing_x
    paused_mancing_x = False

    try:
        while True:
            # 🔒 cek status tiap loop supaya bisa dimatikan kapan pun
            if not state["sg_merge"]["aktif"]:
                print(f"{waktu()} ⏹️ Auto SG Merge dimatikan secara manual.")
                break
            # 🔸 PAUSE MANCING X DI AWAL SIKLUS
            if (not paused_mancing_x 
                and "mancing_x" in state 
                and state["mancing_x"].get("aktif")):
                state["mancing_x"]["pause"] = True
                paused_mancing_x = True
                print(f"{waktu()} ⏸ Pause Auto Mancing X selama 1 siklus SG Merge.")

            print(f"{waktu()} 🔁 Mengecek SkyGarden...")
            
            await asyncio.sleep(5)
            await safe_send_x("/sg_gabung")
            await tunggu_balasan(BOT_X)
            await safe_send_x("/sg_gabung")
            print(f"{waktu()} ⏳ Menunggu balasan /sg_gabung ...")
            await tunggu_balasan(BOT_X)

            ada_buah_untuk_merge = False
            ada_yang_dimerge = False  # 🔹 penanda merge aktif

            # ambil sampai 10 pesan terakhir
            async for event in client.iter_messages(BOT_X, limit=10):
                text = event.raw_text or ""
                if "/sg_merge_" not in text:
                    continue

                baris = re.findall(r"(/sg_merge_\S+)\s+(\d+)x", text)
                ada_buah_untuk_merge = len(baris) > 0
                print(f"{waktu()} 📦 Ditemukan {len(baris)} item buah untuk dicek.")

                for cmd, jumlah_str in baris:
                    if not state["sg_merge"]["aktif"]:
                        print(f"{waktu()} ⏹️ Auto SG Merge dimatikan di tengah proses (awal).")
                        return

                    # pastikan parsing jumlah aman
                    try:
                        jumlah = int(jumlah_str)
                    except Exception:
                        print(f"{waktu()} ⚠️ Gagal parse jumlah untuk {cmd}: '{jumlah_str}' — dilewati.")
                        continue

                    # FILTER LEVEL
                    if not boleh_merge(cmd):
                        nama_debug = cmd.replace("/sg_merge_", "", 1)
                        level_debug = ambil_level(nama_debug)
                        print(f"{waktu()} ⛔ {cmd} dilewati (LEVEL {level_debug} terlalu tinggi)")
                        continue

                    # Filter jumlah < 5
                    if jumlah < 5:
                        print(f"{waktu()} ⏭️ {cmd} dilewati (jumlah {jumlah} < 5)")
                        continue

                    # 🔢 Hitung berapa kali maksimal bisa merge 5 buah
                    max_merge = jumlah // 5
                    ada_yang_dimerge = True
                    
                    print(f"{waktu()} 🍇 Mulai merge {cmd} — total buah {jumlah}, rencana merge {max_merge}x")

                    # 🔁 Lakukan merge sebanyak max_merge kali
                    for i in range(max_merge):
                        if not state["sg_merge"]["aktif"]:
                            print(f"{waktu()} ⏹️ Auto SG Merge dimatikan di tengah proses merge {cmd}.")
                            return

                        # kirim perintah merge
                        await safe_send_x(cmd)
                        print(f"{waktu()} 📤 [{i+1}/{max_merge}] Queue → {cmd}")

                        # tunggu balasan baru dari bot (boleh kamu gedein timeout-nya kalau perlu)
                        await tunggu_balasan(BOT_X)
                        await asyncio.sleep(1.1)

                        # baca pesan terakhir dan klik tombol Gabung 5 bila ada
                        msg = await client.get_messages(BOT_X, limit=1)
                        if msg:
                            msg = msg[0]
                            if msg.buttons:
                                tombol_ditemukan = False
                                for row in msg.buttons:
                                    for btn in row:
                                        if "Gabung 5" in (btn.text or ""):
                                            tombol_ditemukan = True
                                            print(
                                                f"{waktu()} ⚡ Klik 'Gabung ' ({cmd}) — iterasi "
                                                f"{i+1}/{max_merge}"
                                            )
                                            # klik tombol asinkron
                                            asyncio.create_task(btn.click())
                                            break
                                    if tombol_ditemukan:
                                        break

                                if not tombol_ditemukan:
                                    print(
                                        f"{waktu()} ⚠️ [{i+1}/{max_merge}] Tombol 'Gabung 5' "
                                        f"tidak ditemukan di pesan terakhir."
                                    )
                            else:
                                print(
                                    f"{waktu()} ⚠️ [{i+1}/{max_merge}] Tidak ada tombol di pesan terakhir."
                                )
                        else:
                            print(
                                f"{waktu()} ⚠️ [{i+1}/{max_merge}] Tidak ada pesan balasan yang bisa dibaca."
                            )

                        await asyncio.sleep(random.uniform(1.0, 1.3))

                    print(f"{waktu()} 🍀 Selesai rencana merge untuk {cmd} (coba {max_merge}x)")

                break

            # === CEK ULANG SAMPAI BENAR-BENAR HABIS ===
            if ada_buah_untuk_merge and ada_yang_dimerge:
                if not state["sg_merge"]["aktif"]:
                    break

                print(f"{waktu()} 🔁 Mengecek ulang hasil merge...")
                await asyncio.sleep(3)
                await safe_send_x("/sg_gabung")
                await asyncio.sleep(3)

                teks_cek = ""
                async for event in client.iter_messages(BOT_X, limit=5):
                    teks_cek += event.raw_text or ""

                if "/sg_merge_" in teks_cek:
                    print(f"{waktu()} 🍏 Masih ada buah tersisa — lanjut merge lagi.")
                    continue  # kembali ke while utama tanpa tunggu 1 jam
                else:
                    print(f"{waktu()} 🌾 Semua buah sudah habis — tidak ada yang bisa digabung.")

            elif not ada_yang_dimerge:
                print(f"{waktu()} ✅ Tidak ada buah dengan jumlah >= 5 — skip dan tunggu 1/2 jam.")

            # 🔸 SAMPAI DI SINI, SIKLUS MERGE BERES → LANJUTKAN MANCING X KALAU TADI DIPAUSe
            if paused_mancing_x:
                if "mancing_x" in state and "pause" in state["mancing_x"]:
                    state["mancing_x"]["pause"] = False
                paused_mancing_x = False
                print(f"{waktu()} ▶️ Lanjut Auto Mancing X setelah SG Merge selesai.")

            if not state["sg_merge"]["aktif"]:
                break

            print(f"{waktu()} 💤 Menunggu 1 jam sebelum cek berikutnya...")

            # 💡 selama nunggu 1 jam, tetap cek apakah dimatikan
            for _ in range(1 * 60 * 30):  # 1800 detik
                if not state["sg_merge"]["aktif"]:
                    print(f"{waktu()} ⏹️ Auto SG Merge dimatikan saat masa tunggu.")
                    raise asyncio.CancelledError
                await asyncio.sleep(1)

    except asyncio.CancelledError:
        pass

    except Exception as e:
        print(f"{waktu()} [ERROR LOOP SG MERGE ULTRA] {e}")

    finally:
        # jaga-jaga kalau SGM mati pas lagi nge-pause mancing_x
        if paused_mancing_x and "mancing_x" in state and "pause" in state["mancing_x"]:
            state["mancing_x"]["pause"] = False
            print(f"{waktu()} ▶️ Cleanup: Lanjut Auto Mancing X (loop SGM berhenti).")

        sg_merge_running = False
        print(f"{waktu()} ✅ Loop SG Merge berhenti sepenuhnya.")


# === LOOP CMD BEBAS ===
cb_loop_running = False
cb_tasks = {}

# === LOOP CUSTOM COMMAND (CB) ===
async def loop_cb_handler(client, BOT_X, state, safe_send_x):
    global cb_loop_running, cb_tasks

    if cb_loop_running:
        print(f"{waktu()} ⚠️ Loop CB sudah berjalan.")
        return

    cb_loop_running = True
    print(f"{waktu()} 🚀 Loop CB (Custom Command) aktif — ketik perintah dengan format /cmd interval.")

    try:
        while state["cb"]["aktif"]:
            await asyncio.sleep(1)  # idle loop ringan
        print(f"{waktu()} ⏹️ Loop CB dimatikan.")
    except Exception as e:
        print(f"{waktu()} [ERROR LOOP CB] {e}")
    finally:
        cb_loop_running = False
        # hentikan semua task
        for cmd, task in cb_tasks.items():
            task.cancel()
        cb_tasks.clear()
        print(f"{waktu()} ✅ Semua CB task dibersihkan.")

# === MENAMBAH COMMAND BARU ===
async def start_cb_command(cmd_text, interval_menit, safe_send_x):
    global cb_tasks

    # jika sudah ada command sama, hentikan dulu
    if cmd_text in cb_tasks:
        cb_tasks[cmd_text].cancel()
        print(f"{waktu()} 🔁 Reset loop lama untuk {cmd_text}")

    async def cb_task():
        print(f"{waktu()} 🌀 Mulai loop: {cmd_text} setiap {interval_menit} menit")
        while True:
            await safe_send_x(cmd_text)
            print(f"{waktu()} 📤 Kirim: {cmd_text}")
            await asyncio.sleep(interval_menit * 60)

    task = asyncio.create_task(cb_task())
    cb_tasks[cmd_text] = task

# === MENGHENTIKAN SEMUA CB ===
async def stop_all_cb():
    global cb_tasks
    for cmd, task in cb_tasks.items():
        task.cancel()
    cb_tasks.clear()
    print(f"{waktu()} 🛑 Semua custom command dihentikan.")


# === LOOP TERNAK ===
async def loop_ternak():
    data = state["ternak"]
    print(">> Loop ternak dimulai")
    await client.send_message(PRIVATE_LOG_CHAT, "🐓 Auto Ternak dimulai")
    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        await safe_send("/ambilHasil")
        await asyncio.sleep(2)
        await safe_send("/beriMakan")
        await asyncio.sleep(data["interval"])
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    print(">> Loop Ternak berhenti")
    await client.send_message(PRIVATE_LOG_CHAT, "🐓 Auto Ternak dimatikan")

# === LOOP MASAK ===
async def loop_masak():
    data = state["masak"]
    print(">> Loop Masak Alpha dimulai")
    while data["aktif"] and data["kode"] and (data["count"] < data["loops"] or data["loops"] == 0):
        while data.get("pause", False):
            await asyncio.sleep(5)
        await safe_send(data["kode"], BOT_USERNAME)
        data["count"] += 1
        print(f"🍳 Masak ke-{data['count']}")
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    data["aktif"] = False
    await client.send_message(PRIVATE_LOG_CHAT, f"✅ Masak selesai ({data['count']}x)")
    print(">> Loop Masak berhenti")

# === LOOP MASAK X ===
async def loop_masak_x():
    data = state["masak_x"]
    print(">> Loop Masak X dimulai")
    while data["aktif"] and data["kode"] and (data["count"] < data["loops"] or data["loops"] == 0):
        while data.get("pause", False):
            await asyncio.sleep(5)
        await safe_send_x(data["kode"], BOT_X)
        data["count"] += 1
        print(f"🍳 Masak ke-{data['count']}")
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    data["aktif"] = False
    await client.send_message(PRIVATE_LOG_CHAT, f"✅ Masak selesai ({data['count']}x)")
    print(">> Loop Masak berhenti")



# === LOOP MANCING ===
# === LOOP MANCING (ALPHA) — MODEL SG MERGE ===
async def loop_mancing():
    data = state["mancing"]
    lokasi = data.get("lokasi")
    alat = (data.get("alat") or "pancing").lower()

    print(f"{waktu()} >> Loop Mancing Alpha dimulai di {lokasi} pakai {alat.capitalize()} (Bot: {BOT_USERNAME})")

    while data.get("aktif", False):
        # Pause global (misal saat energi habis)
        while data.get("pause", False):
            await asyncio.sleep(5)
        await asyncio.sleep(0.7)

        if not data.get("lokasi"):
            print(f"{waktu()} ⚠️ Lokasi kosong di state['mancing'], hentikan loop.")
            break

        lokasi = data["lokasi"]

        # 1️⃣ Kirim lokasi (mulai mancing)
        await safe_send(lokasi, BOT_USERNAME)
        print(f"{waktu()} 🎣 [Alpha] Kirim lokasi: {lokasi}")

        # 2️⃣ Tunggu balasan dari bot game (bisa pesan "mulai memancing" atau langsung yang ada tombol)
        await tunggu_balasan(BOT_USERNAME, timeout=10)
        await asyncio.sleep(1.1)

        # 3️⃣ Baca pesan terakhir dan cari tombol "Tarik ..."
        msg = await client.get_messages(BOT_USERNAME, limit=1)
        if msg:
            msg = msg[0]
            if msg.buttons:
                tombol_ditemukan = False
                for row in msg.buttons:
                    for btn in row:
                        teks_btn = (btn.text or "").lower()
                        if alat == "pancing" and ("tarik alat pancing" in teks_btn or "pull the rod" in teks_btn):
                            tombol_ditemukan = True
                            await human_sleep()
                            asyncio.create_task(btn.click())
                            print(f"{waktu()} ⚡ [Alpha] Klik 'Tarik Alat Pancing'")
                            break
                        elif alat == "jala" and ("tarik jala" in teks_btn or "pull the net" in teks_btn):
                            tombol_ditemukan = True
                            await human_sleep()
                            asyncio.create_task(btn.click())
                            print(f"{waktu()} ⚡ [Alpha] Klik 'Tarik Jala'")
                            break
                    if tombol_ditemukan:
                        break

                if not tombol_ditemukan:
                    print(f"{waktu()} ⚠️ [Alpha] Tombol Tarik tidak ditemukan di pesan terakhir.")
            else:
                print(f"{waktu()} ⚠️ [Alpha] Tidak ada tombol di pesan terakhir.")
        else:
            print(f"{waktu()} ⚠️ [Alpha] Tidak ada pesan balasan yang bisa dibaca.")

        # 4️⃣ Jeda kecil sebelum siklus berikutnya (biar nggak spam)
        await asyncio.sleep(random.uniform(1.0, 1.5))

    print(f"{waktu()} >> Loop Mancing Alpha berhenti")
    await client.send_message(PRIVATE_LOG_CHAT, "🎣 Auto Mancing Alpha berhenti.")

# === LOOP MANCING (X) — MODEL SG MERGE ===
async def loop_mancing_x():
    data = state["mancing_x"]
    lokasi = data.get("lokasi")
    alat = (data.get("alat") or "pancing").lower()

    print(f"{waktu()} >> Loop Mancing X dimulai di {lokasi} pakai {alat.capitalize()} (Bot: {BOT_X})")

    while data.get("aktif", False):
        while data.get("pause", False):
            await asyncio.sleep(5)

        if not data.get("lokasi"):
            print(f"{waktu()} ⚠️ Lokasi kosong di state['mancing_x'], hentikan loop.")
            break

        lokasi = data["lokasi"]

        # 1️⃣ Kirim lokasi (mulai mancing)
        await safe_send_x(lokasi, BOT_X)
        print(f"{waktu()} 🎣 [X] Kirim lokasi: {lokasi}")

        # 2️⃣ Tunggu balasan dari bot game
        await tunggu_balasan(BOT_X, timeout=10)
        await asyncio.sleep(1.1)

        # 3️⃣ Baca pesan terakhir dan cari tombol "Tarik ..."
        msg = await client.get_messages(BOT_X, limit=1)
        if msg:
            msg = msg[0]
            if msg.buttons:
                tombol_ditemukan = False
                for row in msg.buttons:
                    for btn in row:
                        teks_btn = (btn.text or "").lower()
                        if alat == "pancing" and ("tarik alat pancing" in teks_btn or "pull the rod" in teks_btn):
                            tombol_ditemukan = True
                            await human_sleep()
                            asyncio.create_task(btn.click())
                            print(f"{waktu()} ⚡ [X] Klik 'Tarik Alat Pancing'")
                            break
                        elif alat == "jala" and ("tarik jala" in teks_btn or "pull the net" in teks_btn):
                            tombol_ditemukan = True
                            await human_sleep()
                            asyncio.create_task(btn.click())
                            print(f"{waktu()} ⚡ [X] Klik 'Tarik Jala'")
                            break
                    if tombol_ditemukan:
                        break

                if not tombol_ditemukan:
                    print(f"{waktu()} ⚠️ [X] Tombol Tarik tidak ditemukan di pesan terakhir.")
            else:
                print(f"{waktu()} ⚠️ [X] Tidak ada tombol di pesan terakhir.")
        else:
            print(f"{waktu()} ⚠️ [X] Tidak ada pesan balasan yang bisa dibaca.")

        # 4️⃣ Jeda kecil sebelum siklus berikutnya
        await asyncio.sleep(random.uniform(1.0, 1.3))

    print(f"{waktu()} >> Loop Mancing X berhenti")
    await client.send_message(PRIVATE_LOG_CHAT, "🎣 Auto Mancing X berhenti.")


# === LOOP MACUL (PRIBADI / GUILD / GLOBAL) ===
async def loop_macul(name="macul"):
    data = state[name]
    durasi = data.get("durasi", 180)
    target = data.get("target", BOT_USERNAME)
    print(f">> Mulai {name}: {data['tanaman']} ({data['jumlah']} pohon, {durasi}s)")
    await safe_send(f"🌱 Mulai {name}: {data['tanaman']} ({data['jumlah']} pohon, {durasi}s)", PRIVATE_LOG_CHAT)
    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        if name == "macul_global":
            await safe_send_cepat(f"/tanam_{data['tanaman']}_{data['jumlah']}", GLOBAL_GROUP)
            await asyncio.sleep(durasi)
            await safe_send_cepat("/panen", GLOBAL_GROUP)
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
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    print(f">> Loop {name} berhenti")


# === LOOP GREENHOUSE ===
async def loop_greenhouse():
    data = state["greenhouse"]
    durasi = data.get("durasi", 180)
    print(f">> Mulai Greenhouse: {data['tanaman']} ({data['jumlah']} pohon, {durasi}s)")
    
    while data["aktif"]:
        while data.get("pause", False):
            await asyncio.sleep(5)
        await safe_send(f"/gh_1_tanam_{data['tanaman']}_{data['jumlah']}", BOT_USERNAME)
        await asyncio.sleep(durasi)
        await safe_send("/gh_1_panen", BOT_USERNAME)
        for _ in range(10):  
            if not data["aktif"]:
                break
            await asyncio.sleep(0.5)
    print(">> Loop Greenhouse berhenti")






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

        # === SEMUA ON ===
    if lmsg in ("semua on", "/semua on"):
        # === SKY GARDEN ===
        if not state["skygarden"]["aktif"]:
            state["skygarden"]["aktif"] = True
            asyncio.create_task(loop_skygarden())
            

        # === TERNAK ===
        if not state["ternak"]["aktif"]:
            state["ternak"]["aktif"] = True
            asyncio.create_task(loop_ternak())
            

        # === TERNAK KHUSUS ===
        if not state["ternakkhusus"]["aktif"]:
            state["ternakkhusus"]["aktif"] = True
            asyncio.create_task(loop_ternakkhusus())
            

        # === FISHING GRUP DANAU ===
        if not state["fishing"]["aktif"]:
            state["fishing"]["aktif"] = True
            asyncio.create_task(loop_grup_danau())

        # === ANIMAL HOUSE ===
        if not state["animalhouse"]["aktif"]:
            state["animalhouse"]["aktif"] = True
            asyncio.create_task(loop_animalhouse())

            await event.reply("✅ Semua loop diaktifkan.")
            

        return


    # === SEMUA OFF ===
    if lmsg in ("semua off", "/semua off"):
        stop_msgs = []
        # === FISHING GRUP DANAU ===
        if state["fishing"]["aktif"]:
            state["fishing"]["aktif"] = False
            stop_msgs.append("🎣 Auto Mancing Grup Danau dimatikan.")

        # === SKY GARDEN ===
        if state["skygarden"]["aktif"]:
            state["skygarden"]["aktif"] = False
            stop_msgs.append("🌿 Auto Sky Garden dimatikan.")
              
        # === TERNAK ===
        if state["ternak"]["aktif"]:
            state["ternak"]["aktif"] = False
            stop_msgs.append("🐓 Auto Makan Ternak dimatikan.")

        # === TERNAK KHUSUS ===
        if state["ternakkhusus"]["aktif"]:
            state["ternakkhusus"]["aktif"] = False
            stop_msgs.append("🐮 Auto Ternak Khusus dimatikan.")

        # === ANIMAL HOUSE ===
        if state["animalhouse"]["aktif"]:
            state["animalhouse"]["aktif"] = False
            stop_msgs.append("🏠 Auto Animal House dimatikan.")

        if stop_msgs:
            await event.reply("\n".join(stop_msgs))
        else:
            await event.reply("❗ Tidak ada loop yang aktif untuk dimatikan.")

        return


    # === TERNAK KHUSUS ===
    if lmsg in ("tk on", "/tk on","semua on", "/semua on"):
        if not state["ternakkhusus"]["aktif"]:
            state["ternakkhusus"]["aktif"] = True
            await event.reply("🐮 Auto Ternak Khusus diaktifkan.")
            asyncio.create_task(loop_ternakkhusus())
        else:
            await event.reply("❗ Auto Ternak Khusus sudah aktif.")
        return

    if lmsg in ("tk off", "/tk off", "semua off", "/semua off"):
        if state["ternakkhusus"]["aktif"]:
            state["ternakkhusus"]["aktif"] = False
            await event.reply("⏹ Auto Ternak Khusus dimatikan.")
        else:
            await event.reply("❗ Auto Ternak Khusus belum aktif.")
        return

    # === TERNAK ===
    if lmsg in ("tr on", "/tr on", "semua on","/semua on"):
        if not state["ternak"]["aktif"]:
            state["ternak"]["aktif"] = True
            await event.reply("🐓 Auto Makan Ternak diaktifkan.")
            asyncio.create_task(loop_ternak())
        else:
            await event.reply("❗ Auto Makan Ternak sudah aktif.")
        return

    if lmsg in ("tr off", "/tr off", "semua off","/semua off"):
        if state["ternak"]["aktif"]:
            state["ternak"]["aktif"] = False
            await event.reply("⏹ Auto Makan Ternak dimatikan.")
        else:
            await event.reply("❗ Auto Makan Ternak belum aktif.")
        return

    # === Maling ===
    if lmsg in ("maling on", "/maling on", "semua on","/semua on"):
        if not state["maling"]["aktif"]:
            state["maling"]["aktif"] = True
            await event.reply("🦹‍♂️ Auto Maling diaktifkan.")
            asyncio.create_task(loop_maling())
        else:
            await event.reply("❗ Auto Maling sudah aktif.")
        return
    
    if lmsg in ("maling off", "/maling off", "semua off","/semua off"):
        if state["maling"]["aktif"]:
            state["maling"]["aktif"] = False
            await event.reply("⏹ Auto Maling dimatikan.")
        else:
            await event.reply("❗ Auto Maling belum aktif.")
        return

    # === FISHING GRUP DANAU ===
    if lmsg in ("fd on", "/fd on", "semua on","/semua on"):
        if not state["fishing"]["aktif"]:
            state["fishing"]["aktif"] = True
            await event.reply("🎣 Auto Mancing Grup Danau diaktifkan.")
            asyncio.create_task(loop_grup_danau())
        else:
            await event.reply("❗ Auto Mancing Grup Danau sudah aktif.")
        return
    
    if lmsg in ("fd off", "/fd off", "semua off","/semua off"):
        if state["fishing"]["aktif"]:
            state["fishing"]["aktif"] = False
            await event.reply("⏹ Auto Mancing Grup Danau dimatikan.")
        else:
            await event.reply("❗ Auto Mancing Grup Danau belum aktif.")
        return

    # === ANIMAL HOUSE ===
    if lmsg in ("ah on", "/ah on", "semua on","/semua on"):
        if not state["animalhouse"]["aktif"]:
            state["animalhouse"]["aktif"] = True
            await event.reply("🏠 Auto Animal House diaktifkan.")
            asyncio.create_task(loop_animalhouse())
        else:
            await event.reply("❗ Auto Animal House sudah aktif.")
        return
    
    if lmsg in ("ah off", "/ah off", "semua off","/semua off"):
        if state["animalhouse"]["aktif"]:
            state["animalhouse"]["aktif"] = False
            await event.reply("⏹ Auto Animal House dimatikan.")
        else:
            await event.reply("❗ Auto Animal House belum aktif.")
        return

    # === SKY GARDEN ===
    if lmsg in ("sg on", "/sg on", "semua on","/semua on"):
        if not state["skygarden"]["aktif"]:
            state["skygarden"]["aktif"] = True
            await event.reply("🌿 Auto Sky Garden diaktifkan.")
            asyncio.create_task(loop_skygarden())
        else:
            await event.reply("❗ Auto Sky Garden sudah aktif.")
        return

    if lmsg in ("sg off", "/sg off", "semua off","/semua off"):
        if state["skygarden"]["aktif"]:
            state["skygarden"]["aktif"] = False
            await event.reply("⏹ Auto Sky Garden dimatikan.")
        else:
            await event.reply("❗ Auto Sky Garden belum aktif.")
        return
    
    # === SG UPGRADE ===
    if lmsg in ("sgu on", "/sgu on"):
        if not state["sg_upgrade"]["aktif"]:
            state["sg_upgrade"]["aktif"] = True
            await event.reply("🚀 Auto SG Upgrade diaktifkan.")
            asyncio.create_task(loop_sg_upgrade())
        else:
            await event.reply("❗ Auto SG Upgrade sudah aktif.")
        return
    
    if lmsg in ("sgu off", "/sgu off"):
        if state["sg_upgrade"]["aktif"]:
            state["sg_upgrade"]["aktif"] = False
            await event.reply("⏹ Auto SG Upgrade dimatikan.")
        else:
            await event.reply("❗ Auto SG Upgrade belum aktif.")
        return

    # === SG MERGE ===
    if lmsg in ("sgm on", "/sgm on"):
        if not state["sg_merge"]["aktif"]:
            state["sg_merge"]["aktif"] = True
            await event.reply("🌿 Auto SG Merge diaktifkan (setiap 1 jam).")
            asyncio.create_task(loop_sg_merge(client, BOT_X, state))
        else:
            await event.reply("❗ Auto SG Merge sudah aktif.")
        return
    
    if lmsg in ("sgm off", "/sgm off"):
        if state["sg_merge"]["aktif"]:
            state["sg_merge"]["aktif"] = False
            await event.reply("⏹ Auto SG Merge dimatikan.")
        else:
            await event.reply("❗ Auto SG Merge belum aktif.")
        return

    # === CB (CUSTOM COMMAND) ===
    if lmsg in ("cb on", "/cb on"):
        if not state["cb"]["aktif"]:
            state["cb"]["aktif"] = True
            await event.reply("🚀 Loop CB (Custom Command) diaktifkan.")
            asyncio.create_task(loop_cb_handler(client, BOT_X, state, safe_send_x))
        else:
            await event.reply("❗ Loop CB sudah aktif.")
        return
    
    if lmsg in ("cb off", "/cb off"):
        if state["cb"]["aktif"]:
            state["cb"]["aktif"] = False
            await stop_all_cb()
            await event.reply("⏹ Loop CB dimatikan.")
        else:
            await event.reply("❗ Loop CB belum aktif.")
        return
    
    # === PARSING CUSTOM CMD ===
    # Contoh format: /makan_HidanganRaja_1 60  → kirim tiap 60 menit
    if lmsg.startswith("/"):
        match = re.match(r"(/[\w_]+)\s+(\d+)", lmsg)
        if match and state["cb"]["aktif"]:
            cmd_text = match.group(1)
            interval = int(match.group(2))
            await start_cb_command(cmd_text, interval, safe_send_x)
            await event.reply(f"✅ Menambahkan perintah `{cmd_text}` setiap {interval} menit.")
        elif match and not state["cb"]["aktif"]:
            await event.reply("⚠️ Nyalakan dulu CB Loop dengan `cb on`.")
        return

    # === MASAK ===
    if lmsg == "masak":
        state["masak"].update({
            "aktif": False,
            "kode": None,
            "loops": 0,
            "count": 0,
            "menunggu_input": "kode"
        })
        await event.reply("🍳 Mau masak apa?")
        return

    # Jika sedang menunggu kode masakan
    if state["masak"].get("menunggu_input") == "kode":
        state["masak"]["kode"] = msg
        state["masak"]["menunggu_input"] = "jumlah"
        await event.reply("🔁 Mau masak berapa kali?")
        return

    # Jika sedang menunggu jumlah loop
    if state["masak"].get("menunggu_input") == "jumlah" and lmsg.isdigit():
        loops = int(lmsg)
        state["masak"].update({
            "aktif": True,
            "loops": loops,
            "count": 0,
            "menunggu_input": False
        })
        await event.reply(f"Mulai auto-masak {loops}x 🍳")
        asyncio.create_task(loop_masak())
        return

    # === MASAK X ===
    if lmsg == "masak x":
        state["masak_x"].update({
            "aktif": False,
            "kode": None,
            "loops": 0,
            "count": 0,
            "menunggu_input": "kode"
        })
        await event.reply("🍳 Mau masak apa?")
        return

    # Jika sedang menunggu kode masakan
    if state["masak_x"].get("menunggu_input") == "kode":
        state["masak_x"]["kode"] = msg
        state["masak_x"]["menunggu_input"] = "jumlah"
        await event.reply("🔁 Mau masak berapa kali?")
        return

    # Jika sedang menunggu jumlah loop
    if state["masak_x"].get("menunggu_input") == "jumlah" and lmsg.isdigit():
        loops = int(lmsg)
        state["masak_x"].update({
            "aktif": True,
            "loops": loops,
            "count": 0,
            "menunggu_input": False
        })
        await event.reply(f"Mulai auto-masak {loops}x 🍳")
        asyncio.create_task(loop_masak_x())
        return


    # === MANCING ===
    if lmsg == "mancing":
        state["mancing"].update({
            "aktif": False,
            "lokasi": None,
            "alat": None,
            "menunggu_lokasi": True,
            "menunggu_alat": False
        })

        await event.reply("🎣 Mancing dimana?")
        return
    
    # Tahap 1 → Pilih lokasi
    if state["mancing"].get("menunggu_lokasi", False) and not state["mancing"]["aktif"]:
        lokasi = msg.strip()
        state["mancing"]["lokasi"] = lokasi
        state["mancing"]["menunggu_lokasi"] = False
        state["mancing"]["menunggu_alat"] = True
        await event.reply(f"📍 Lokasi: {lokasi}\nPakai alat apa? (Ketik **Pancing** atau **Jala**)")
        return

    # Tahap 2 → Pilih alat
    if state["mancing"].get("menunggu_alat", False) and not state["mancing"]["aktif"]:
        alat = msg.strip().lower()
        if alat not in ("pancing", "jala"):
            await event.reply("⚠️ Pilihan tidak valid! Ketik **Pancing** atau **Jala**.")
            return
        
        state["mancing"]["alat"] = alat
        state["mancing"]["aktif"] = True
        state["mancing"]["menunggu_alat"] = False

        lokasi = state["mancing"]["lokasi"]
        await event.reply(f"🎣 Mulai auto-mancing di {lokasi} pakai {alat.capitalize()}...")
        asyncio.create_task(loop_mancing())
        return


    # === MANCING X ===
    if lmsg == "mancing x":
        state["mancing_x"].update({
            "aktif": False,
            "lokasi": None,
            "alat": None,
            "menunggu_lokasi": True,
            "menunggu_alat": False
        })

        await event.reply("🎣 Mancing dimana?")
        return
    
    # Tahap 1 → Pilih lokasi
    if state["mancing_x"].get("menunggu_lokasi", False) and not state["mancing_x"]["aktif"]:
        lokasi = msg.strip()
        state["mancing_x"]["lokasi"] = lokasi
        state["mancing_x"]["menunggu_lokasi"] = False
        state["mancing_x"]["menunggu_alat"] = True
        await event.reply(f"📍 Lokasi: {lokasi}\nPakai alat apa? (Ketik **Pancing** atau **Jala**)")
        return

    # Tahap 2 → Pilih alat
    if state["mancing_x"].get("menunggu_alat", False) and not state["mancing_x"]["aktif"]:
        alat = msg.strip().lower()
        if alat not in ("pancing", "jala"):
            await event.reply("⚠️ Pilihan tidak valid! Ketik **Pancing** atau **Jala**.")
            return
        state["mancing_x"]["alat"] = alat
        state["mancing_x"]["aktif"] = True
        state["mancing_x"]["menunggu_alat"] = False

        lokasi = state["mancing_x"]["lokasi"]
        await event.reply(f"🎣 Mulai auto-mancing di {lokasi} pakai {alat.capitalize()}...")
        asyncio.create_task(loop_mancing_x())
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

    # === GREENHOUSE ===
    if lmsg == "gh":
        load_tanaman()
        state["greenhouse"].update({"aktif": False, "tanaman": None, "jumlah": 0, "durasi": 180, "menunggu_input": True})
        await event.reply("🌱 Mau tanam apa di Greenhouse? (gh <nama> <jumlah>)")
        return
    
    # One-line format: gh <nama> <jumlah>
    if lmsg.startswith("gh ") or lmsg.startswith("/gh "):
        parts = msg.replace("/","").split()
        if len(parts)>=3 and parts[1].strip() and parts[2].isdigit():
            tanaman = parts[1].strip().lower()
            jumlah = int(parts[2])
            durasi = tanaman_data.get(tanaman, 180)
            state["greenhouse"].update({
                "aktif": True,
                "tanaman": tanaman,
                "jumlah": jumlah,
                "durasi": durasi,
                "menunggu_input": False
            })
            await event.reply(f"🌱 Mulai Greenhouse {tanaman} ({jumlah} pohon, {durasi}s)")
            asyncio.create_task(loop_greenhouse())
            return
        else:
            await event.reply("Format: gh <nama> <jumlah>")
            return



    # === STOP ALL ===
    if lmsg.startswith("stop"):
        parts = lmsg.split()
        if len(parts) == 1 or parts[0] in ("stop_all", "/stop_all"):
            stop_all()
            await event.reply("⏹ Semua loop dihentikan.")
            return

        # contoh: stop mancing_x atau stop mancing x
        mode = parts[1] if len(parts) > 1 else None
        if len(parts) > 2:
            mode += f"_{parts[2]}"

        if mode and mode in state and state[mode]["aktif"]:
            state[mode]["aktif"] = False
            await event.reply(f"⏹ Loop {mode} dihentikan.")
        else:
            await event.reply("❗ Tidak ada loop aktif / format salah.")
        return

        
    print(f"❗ Perintah tidak dikenali: {msg}")



# ---------------- BOT HANDLER ----------------
# === EVENT HANDLER RESTORE ===
@client.on(events.NewMessage(incoming=True, chats=BOT_USERNAME))
async def handle_restore(event):
    msg = (event.raw_text or "").lower()

        # Jika energi habis
    if "/tidur" in msg or "/sleep" in msg:
        print("⚠️ Energi habis, mencoba restore...")
        state["energi_habis"] = True
        for v in state.values():
            if isinstance(v, dict) and "pause" in v:
                v["pause"] = True
        for i in range(10):
            await asyncio.sleep(3)
            if not state.get("energi_habis", True):
                print("🛑 Energi sudah pulih, hentikan percobaan restore.")
                break
            await safe_send_cepat("restore", BOT_USERNAME)
            print(f"[RESTORE TRY] {i+1}/10")
            await asyncio.sleep(5)
        return

    # Jika sudah berhasil dipulihkan
    if "berhasil dipulihkan" in msg or "energi berhasil dipulihkan" in msg:
        print("✅ Energi berhasil dipulihkan (global)")
        state["energi_habis"] = False
        for v in state.values():
            if isinstance(v, dict) and "pause" in v:
                v["pause"] = False

# ==== HANDLER BOT X SG UPGRADE ====
@client.on(events.NewMessage(incoming=True, chats=BOT_X))
async def handle_sg_upgrade_x(event):
    msg = (event.raw_text or "").lower()
    data = state.get("sg_upgrade", {})
    if not data.get("aktif"):
        return

    # Klik tombol confirm hanya jika pesan berhubungan dengan upgrade
    if "upgrade keranjang buah" in msg or "menggunakan 5" in msg:
        if event.buttons:
            for row in event.buttons:
                for btn in row:
                    if (btn.text or "").lower() == "confirm":
                        await btn.click()
                        print("⚡ Klik Confirm Upgrade")
                        return

    # Jika upgrade berhasil
    if "berhasil mengupgrade keranjang" in msg or "keranjang buah menjadi" in msg or "/sg_keranjangbuah" in msg:
        await asyncio.sleep(1.5)
        await safe_send_x("/sg_upgrade", BOT_X)
        print("✅ SG Upgrade berhasil → lanjut upgrade")
        return

    if any(x in msg for x in [
        "kamu memerlukan 5", "untuk mengupgrade keranjang"
    ]):
        if data.get("aktif"):
            print("⚠️ Bahan tidak mencukupi! Hentikan loop SG Upgrade.")
            data["aktif"] = False
            return



# ---------------- MAIN ----------------
async def main():
    await client.start(phone=PHONE)
    logger.info("Client started")
    load_tanaman()
    asyncio.create_task(message_worker())
    msg_intro = ("Bot siap ✅\n\nCommand:\n"
                 "- masak → (Bot Alpha)\n"
                 "- masak x → (Bot X)\n"
                 "- mancing → (Bot Alpha)\n"
                 "- mancing x → (Bot X)\n"
                 "- macul <tanaman> <jumlah>\n"
                 "- macul_guild <tanaman> <jumlah>\n"
                 "- macul_global <tanaman> <jumlah>\n"
                 "- sg on / sg off (sky garden)\n"
                 "- sgm on / sgm off (sky garden merge)\n"
                 "- cb on / cb off (custom command loop)\n"
                 "- tk on / tk off (ternak khusus)\n"
                 "- tr on / tr off (ternak biasa)\n"
                 "- fd on / fd off (fishing danau)\n"
                 "- maling on / maling off (auto maling)\n"
                 "- ah on / ah off (animal house)\n"
                 "- gh <tanaman> <jumlah> (greenhouse)\n"
                 "- semua on / semua off\n"
                 "- stop atau stop_[mode]")
    await safe_send(msg_intro, "me")
    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
