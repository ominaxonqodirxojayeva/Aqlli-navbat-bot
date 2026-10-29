import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv
import aiosqlite

import database as db
from keyboards import (
    main_menu, organizations_keyboard, services_keyboard,
    admin_menu, queue_actions_keyboard, back_to_main,
    admin_organizations_keyboard, admin_organization_actions,
    admin_services_keyboard, admin_service_list_keyboard,
    admin_service_actions,
)

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")
TOKEN = os.getenv("9005805007:AAGD1HXihKhoEo_rt7xMWm8EcIZk4yhAYD8", "").strip()
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("8774143442 ", "").split(", 7776591441")
    if value.strip().isdigit()
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

dp = Dispatcher()

class AdminInput(StatesGroup):
    add_org = State()
    rename_org = State()
    add_service = State()
    rename_service = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@dp.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    await db.register_user(user.id, user.full_name, user.username)
    await message.answer(
        f"Assalomu alaykum, <b>{user.full_name}</b>! 👋\n\n"
        "🎫 <b>Aqlli Navbat</b> tizimiga xush kelibsiz.\n"
        "Bu bot orqali tashkilot va xizmatni tanlab, elektron navbat olishingiz mumkin.\n\n"
        "Quyidagi menyudan kerakli bo‘limni tanlang:",
        reply_markup=main_menu(is_admin(user.id)),
    )


@dp.message(Command("help"))
async def help_command(message: Message):
    text = (
        "ℹ️ <b>Botdan foydalanish</b>\n\n"
        "🎫 <b>Navbat olish</b> — tashkilot va xizmatni tanlang.\n"
        "📋 <b>Navbatim</b> — faol navbatingizni ko‘ring.\n"
        "❌ <b>Navbatni bekor qilish</b> — faol navbatni bekor qiling.\n"
        "📞 <b>Aloqa</b> — yordam olish uchun administratorga murojaat qiling.\n\n"
        "Buyruqlar: /start, /help"
    )
    await message.answer(text, reply_markup=back_to_main(is_admin(message.from_user.id)))


@dp.message(F.text == "🎫 Navbat olish")
async def take_queue(message: Message):
    orgs = await db.get_organizations()
    if not orgs:
        await message.answer(
            "Hozircha faol tashkilotlar kiritilmagan. Administratorga murojaat qiling.",
            reply_markup=main_menu(is_admin(message.from_user.id)),
        )
        return
    await message.answer("🏢 <b>Tashkilotni tanlang:</b>", reply_markup=organizations_keyboard(orgs))


@dp.callback_query(F.data.startswith("org:"))
async def choose_org(callback: CallbackQuery):
    try:
        org_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Noto‘g‘ri tanlov.", show_alert=True)
        return
    services = await db.get_services(org_id)
    if not services:
        await callback.answer("Bu tashkilotda hozircha xizmatlar yo‘q.", show_alert=True)
        return
    await callback.message.edit_text(
        "📌 <b>Xizmat turini tanlang:</b>",
        reply_markup=services_keyboard(services, org_id),
    )
    await callback.answer()


@dp.callback_query(F.data == "nav:back_orgs")
async def back_orgs(callback: CallbackQuery):
    orgs = await db.get_organizations()
    await callback.message.edit_text(
        "🏢 <b>Tashkilotni tanlang:</b>",
        reply_markup=organizations_keyboard(orgs),
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("service:"))
async def choose_service(callback: CallbackQuery):
    try:
        _, org_id, service_id = callback.data.split(":")
        result = await db.create_queue(
            callback.from_user.id, int(org_id), int(service_id)
        )
    except (ValueError, IndexError):
        await callback.answer("Tanlovni qayta bajaring.", show_alert=True)
        return

    if result == "ACTIVE_QUEUE":
        await callback.answer(
            "Sizda allaqachon faol navbat bor. Avval uni yakunlang yoki bekor qiling.",
            show_alert=True,
        )
        return
    if result is None:
        await callback.answer("Xizmat topilmadi yoki hozir faol emas.", show_alert=True)
        return

    queue_id, number, org_name, service_name, created_at = result
    position = await db.get_queue_position(queue_id)
    await callback.message.edit_text(
        "✅ <b>Navbatingiz muvaffaqiyatli olindi!</b>\n\n"
        f"🎫 Navbat raqami: <b>{number}</b>\n"
        f"🏢 Tashkilot: {org_name}\n"
        f"📌 Xizmat: {service_name}\n"
        f"👥 Sizdan oldinda: {max(position - 1, 0)} ta navbat\n"
        f"🕒 Olingan vaqt: {created_at}\n\n"
        "Navbat holatini «📋 Navbatim» bo‘limidan kuzatishingiz mumkin.",
        reply_markup=back_to_main(is_admin(callback.from_user.id)),
    )
    await callback.answer("Navbat olindi!")


@dp.message(F.text == "📋 Navbatim")
async def my_queue(message: Message):
    queue = await db.get_user_queue(message.from_user.id)
    if not queue:
        await message.answer(
            "Sizda faol navbat mavjud emas.\nNavbat olish uchun «🎫 Navbat olish» tugmasini bosing.",
            reply_markup=main_menu(is_admin(message.from_user.id)),
        )
        return
    qid, number, status, org_name, service_name, created_at = queue
    position = await db.get_queue_position(qid) if status == "Kutilmoqda" else 0
    extra = f"\n👥 Sizdan oldinda: {max(position - 1, 0)} ta" if status == "Kutilmoqda" else ""
    await message.answer(
        "📋 <b>Sizning faol navbatingiz</b>\n\n"
        f"🎫 Raqam: <b>{number}</b>\n"
        f"🏢 Tashkilot: {org_name}\n"
        f"📌 Xizmat: {service_name}\n"
        f"📊 Holat: <b>{status}</b>{extra}\n"
        f"🕒 Olingan vaqt: {created_at}",
        reply_markup=main_menu(is_admin(message.from_user.id)),
    )


@dp.message(F.text == "❌ Navbatni bekor qilish")
async def cancel_my_queue(message: Message):
    queue = await db.get_user_queue(message.from_user.id)
    if not queue:
        await message.answer("Bekor qilinadigan faol navbatingiz yo‘q.")
        return
    cancelled = await db.cancel_queue(message.from_user.id)
    if cancelled:
        await message.answer(
            f"✅ {queue[1]} raqamli navbatingiz bekor qilindi.",
            reply_markup=main_menu(is_admin(message.from_user.id)),
        )
    else:
        await message.answer("Navbatni bekor qilib bo‘lmadi. Qaytadan urinib ko‘ring.")


@dp.message(F.text == "📞 Aloqa")
async def contact(message: Message):
    admins = ", ".join(f"<code>{i}</code>" for i in sorted(ADMIN_IDS))
    admin_text = f"\nAdministrator ID: {admins}" if admins else ""
    await message.answer(
        "📞 <b>Aloqa va yordam</b>\n\n"
        "Botdan foydalanishda muammo bo‘lsa, administratorga murojaat qiling."
        f"{admin_text}",
        reply_markup=main_menu(is_admin(message.from_user.id)),
    )


@dp.message(Command("admin"))
@dp.message(F.text == "👨‍💻 Admin panel")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Sizda administrator huquqi yo‘q.")
        return
    stats = await db.get_statistics()
    queues = await db.get_waiting_and_called_queues()
    await message.answer(
        "👨‍💻 <b>ADMINISTRATOR PANELI</b>\n\n"
        f"📊 Bugungi jami navbatlar: <b>{stats['total']}</b>\n"
        f"⏳ Kutilayotgan: <b>{stats['waiting']}</b>\n"
        f"📣 Chaqirilgan: <b>{stats['called']}</b>\n"
        f"✅ Yakunlangan: <b>{stats['done']}</b>\n"
        f"❌ Bekor qilingan: <b>{stats['cancelled']}</b>\n\n"
        "Boshqarish uchun quyidagi tugmalardan foydalaning.",
        reply_markup=admin_menu(),
    )
    if queues:
        await message.answer("📋 <b>Faol navbatlar:</b>")
        for q in queues[:20]:
            qid, number, status, user_id, user_name, org_name, service_name, created_at = q
            await message.answer(
                f"🎫 <b>{number}</b> — {status}\n"
                f"👤 {user_name or 'Foydalanuvchi'} (ID: <code>{user_id}</code>)\n"
                f"🏢 {org_name}\n📌 {service_name}\n🕒 {created_at}",
                reply_markup=queue_actions_keyboard(qid, status),
            )
    else:
        await message.answer("Hozircha faol navbatlar yo‘q.")


@dp.callback_query(F.data == "admin:refresh")
async def admin_refresh(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    stats = await db.get_statistics()
    await callback.message.edit_text(
        "👨‍💻 <b>ADMINISTRATOR PANELI</b>\n\n"
        f"📊 Bugungi jami navbatlar: <b>{stats['total']}</b>\n"
        f"⏳ Kutilayotgan: <b>{stats['waiting']}</b>\n"
        f"📣 Chaqirilgan: <b>{stats['called']}</b>\n"
        f"✅ Yakunlangan: <b>{stats['done']}</b>\n"
        f"❌ Bekor qilingan: <b>{stats['cancelled']}</b>",
        reply_markup=admin_menu(),
    )
    await callback.answer("Statistika yangilandi.")


@dp.callback_query(F.data == "admin:next")
async def call_next(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    queue = await db.call_next_queue()
    if not queue:
        await callback.answer("Kutilayotgan navbat yo‘q.", show_alert=True)
        return
    qid, user_id, number, org_name, service_name = queue
    try:
        await bot.send_message(
            user_id,
            "📣 <b>Navbatingiz keldi!</b>\n\n"
            f"🎫 Raqam: <b>{number}</b>\n🏢 {org_name}\n📌 {service_name}\n\n"
            "Iltimos, xizmat ko‘rsatish joyiga boring.",
        )
    except Exception:
        logger.warning("User %s ga navbat xabari yuborilmadi", user_id)
    await callback.answer(f"{number} navbat chaqirildi.")
    await callback.message.answer(
        f"📣 <b>{number}</b> navbat chaqirildi.",
        reply_markup=queue_actions_keyboard(qid, "Chaqirildi"),
    )


@dp.callback_query(F.data.startswith("admin:finish:"))
async def finish_queue(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    try:
        qid = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Navbat ID noto‘g‘ri.", show_alert=True)
        return
    queue = await db.get_queue_by_id(qid)
    if not queue or not await db.finish_queue(qid):
        await callback.answer("Navbat topilmadi yoki allaqachon yakunlangan.", show_alert=True)
        return
    user_id, number, org_name, service_name = queue
    try:
        await bot.send_message(
            user_id,
            f"✅ <b>{number}</b> raqamli navbatingiz yakunlandi.\n"
            f"🏢 {org_name}\n📌 {service_name}\nRahmat!",
        )
    except Exception:
        pass
    await callback.answer("Navbat yakunlandi.")
    await callback.message.edit_text(f"✅ <b>{number}</b> navbat yakunlandi.")


@dp.callback_query(F.data.startswith("admin:cancel:"))
async def admin_cancel_queue(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    try:
        qid = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Navbat ID noto‘g‘ri.", show_alert=True)
        return
    queue = await db.get_queue_by_id(qid)
    if not queue or not await db.admin_cancel_queue(qid):
        await callback.answer("Navbat topilmadi yoki faol emas.", show_alert=True)
        return
    user_id, number, org_name, service_name = queue
    try:
        await bot.send_message(
            user_id,
            f"❌ <b>{number}</b> raqamli navbatingiz administrator tomonidan bekor qilindi.",
        )
    except Exception:
        pass
    await callback.answer("Navbat bekor qilindi.")
    await callback.message.edit_text(f"❌ <b>{number}</b> navbat bekor qilindi.")


@dp.message(Command("addorg"))
async def add_org(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Sizda administrator huquqi yo‘q.")
        return
    name = message.text.partition(" ")[2].strip()
    if not name:
        await message.answer("Foydalanish: <code>/addorg Tashkilot nomi</code>")
        return
    org_id = await db.add_organization(name)
    await message.answer(f"✅ Tashkilot qo‘shildi: <b>{name}</b> (ID: {org_id})")


@dp.message(Command("addservice"))
async def add_service(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Sizda administrator huquqi yo‘q.")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await message.answer(
            "Foydalanish: <code>/addservice TASHKILOT_ID Xizmat nomi</code>\n"
            "Masalan: <code>/addservice 1 Terapevt qabuli</code>"
        )
        return
    org_id = int(parts[1])
    service_name = parts[2].strip()
    service_id = await db.add_service(org_id, service_name)
    if service_id is None:
        await message.answer("Bunday tashkilot topilmadi.")
    else:
        await message.answer(f"✅ Xizmat qo‘shildi: <b>{service_name}</b> (ID: {service_id})")


@dp.message(Command("orgs"))
async def list_orgs(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Sizda administrator huquqi yo‘q.")
        return
    orgs = await db.get_organizations()
    if not orgs:
        await message.answer("Tashkilotlar hali qo‘shilmagan. /addorg orqali qo‘shing.")
        return
    await message.answer(
        "🏢 <b>Tashkilotlar</b>\n\n" +
        "\n".join(f"ID <code>{oid}</code> — {name}" for oid, name in orgs) +
        "\n\nXizmat qo‘shish: <code>/addservice ID Xizmat nomi</code>"
    )




# ---------------- ADMIN: boshqaruv ----------------

async def show_admin_home(message_or_callback):
    stats = await db.get_statistics()
    text = (
        "👨‍💻 <b>ADMINISTRATOR PANELI</b>\n\n"
        f"📊 Bugungi jami navbatlar: <b>{stats['total']}</b>\n"
        f"⏳ Kutilayotgan: <b>{stats['waiting']}</b>\n"
        f"📣 Chaqirilgan: <b>{stats['called']}</b>\n"
        f"✅ Yakunlangan: <b>{stats['done']}</b>\n"
        f"❌ Bekor qilingan: <b>{stats['cancelled']}</b>\n\n"
        "Boshqarish uchun tugmani tanlang."
    )
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.answer(text, reply_markup=admin_menu())
    else:
        await message_or_callback.answer(text, reply_markup=admin_menu())


@dp.callback_query(F.data == "admin:home")
async def admin_home_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    await show_admin_home(callback)
    await callback.answer()


@dp.callback_query(F.data == "admin:organizations")
async def admin_organizations(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    organizations = await db.get_all_organizations()
    await callback.message.answer(
        "🏢 <b>Tashkilotlarni boshqarish</b>",
        reply_markup=admin_organizations_keyboard(
            [(oid, name) for oid, name, active in organizations]
        ),
    )
    await callback.answer()


@dp.callback_query(F.data == "admin:org:add")
async def admin_org_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    await state.set_state(AdminInput.add_org)
    await callback.message.answer("Yangi tashkilot nomini yuboring:")
    await callback.answer()


@dp.message(AdminInput.add_org)
async def admin_org_add_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    name = (message.text or "").strip()
    if not name:
        await message.answer("Nom bo‘sh bo‘lmasin. Qaytadan yuboring:")
        return
    org_id = await db.add_organization(name)
    await state.clear()
    if org_id:
        await message.answer(f"✅ Tashkilot saqlandi: <b>{name}</b> (ID: {org_id})")
    else:
        await message.answer("Tashkilotni saqlab bo‘lmadi. Nomni tekshiring.")


@dp.callback_query(F.data.regexp(r"^admin:org:\d+$"))
async def admin_org_details(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    org_id = int(callback.data.rsplit(":", 1)[1])
    organizations = await db.get_all_organizations()
    org = next((item for item in organizations if item[0] == org_id), None)
    if not org:
        await callback.answer("Tashkilot topilmadi.", show_alert=True)
        return
    _, name, active = org
    await callback.message.answer(
        f"🏢 <b>{name}</b>\nHolati: {'Faol' if active else 'Faol emas'}",
        reply_markup=admin_organization_actions(org_id, bool(active)),
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^admin:org:rename:\d+$"))
async def admin_org_rename_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    org_id = int(callback.data.rsplit(":", 1)[1])
    await state.update_data(org_id=org_id)
    await state.set_state(AdminInput.rename_org)
    await callback.message.answer("Tashkilotning yangi nomini yuboring:")
    await callback.answer()


@dp.message(AdminInput.rename_org)
async def admin_org_rename_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    name = (message.text or "").strip()
    if not name:
        await message.answer("Nom bo‘sh bo‘lmasin. Qaytadan yuboring:")
        return
    ok = await db.rename_organization(data["org_id"], name)
    await state.clear()
    await message.answer("✅ Tashkilot nomi o‘zgartirildi." if ok else "O‘zgartirib bo‘lmadi.")


@dp.callback_query(F.data.regexp(r"^admin:org:toggle:\d+$"))
async def admin_org_toggle(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    org_id = int(callback.data.rsplit(":", 1)[1])
    organizations = await db.get_all_organizations()
    org = next((item for item in organizations if item[0] == org_id), None)
    if not org:
        await callback.answer("Tashkilot topilmadi.", show_alert=True)
        return
    ok = await db.set_organization_active(org_id, not bool(org[2]))
    await callback.answer("Holat yangilandi." if ok else "Amal bajarilmadi.")
    await callback.message.answer("Tashkilot holati yangilandi.")


@dp.callback_query(F.data.regexp(r"^admin:org:delete:\d+$"))
async def admin_org_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    org_id = int(callback.data.rsplit(":", 1)[1])
    ok = await db.delete_organization(org_id)
    await callback.answer(
        "Tashkilot o‘chirildi." if ok else
        "O‘chirilmadi: navbatlar tarixi mavjud yoki tashkilot topilmadi.",
        show_alert=not ok,
    )


@dp.callback_query(F.data == "admin:services")
async def admin_services(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    organizations = await db.get_all_organizations()
    await callback.message.answer(
        "📌 <b>Xizmatlar boshqaruvi</b>\nTashkilotni tanlang:",
        reply_markup=admin_services_keyboard(
            [(oid, name) for oid, name, active in organizations]
        ),
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^admin:services:org:\d+$"))
async def admin_services_for_org(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    org_id = int(callback.data.rsplit(":", 1)[1])
    services = await db.get_all_services(org_id)
    await callback.message.answer(
        "📌 <b>Xizmatlarni tanlang:</b>",
        reply_markup=admin_service_list_keyboard(
            [(sid, name) for sid, name, active in services], org_id
        ),
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^admin:service:add:\d+$"))
async def admin_service_add_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    org_id = int(callback.data.rsplit(":", 1)[1])
    await state.update_data(org_id=org_id)
    await state.set_state(AdminInput.add_service)
    await callback.message.answer("Yangi xizmat nomini yuboring:")
    await callback.answer()


@dp.message(AdminInput.add_service)
async def admin_service_add_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    name = (message.text or "").strip()
    if not name:
        await message.answer("Xizmat nomi bo‘sh bo‘lmasin. Qaytadan yuboring:")
        return
    service_id = await db.add_service(data["org_id"], name)
    await state.clear()
    await message.answer(
        f"✅ Xizmat saqlandi: <b>{name}</b> (ID: {service_id})"
        if service_id else "Xizmat qo‘shilmadi. Tashkilot faol ekanini tekshiring."
    )


@dp.callback_query(F.data.regexp(r"^admin:service:\d+$"))
async def admin_service_details(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    service_id = int(callback.data.rsplit(":", 1)[1])
    service = None
    for org_id, org_name, org_active in await db.get_all_organizations():
        for sid, name, active in await db.get_all_services(org_id):
            if sid == service_id:
                service = (org_id, org_name, name, active)
                break
        if service:
            break
    if not service:
        await callback.answer("Xizmat topilmadi.", show_alert=True)
        return
    _, org_name, name, active = service
    await callback.message.answer(
        f"📌 <b>{name}</b>\n🏢 {org_name}\nHolati: {'Faol' if active else 'Faol emas'}",
        reply_markup=admin_service_actions(service_id, bool(active)),
    )
    await callback.answer()


@dp.callback_query(F.data.regexp(r"^admin:service:rename:\d+$"))
async def admin_service_rename_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    service_id = int(callback.data.rsplit(":", 1)[1])
    await state.update_data(service_id=service_id)
    await state.set_state(AdminInput.rename_service)
    await callback.message.answer("Xizmatning yangi nomini yuboring:")
    await callback.answer()


@dp.message(AdminInput.rename_service)
async def admin_service_rename_finish(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await state.clear()
        return
    data = await state.get_data()
    name = (message.text or "").strip()
    if not name:
        await message.answer("Nom bo‘sh bo‘lmasin. Qaytadan yuboring:")
        return
    ok = await db.rename_service(data["service_id"], name)
    await state.clear()
    await message.answer("✅ Xizmat nomi o‘zgartirildi." if ok else "O‘zgartirib bo‘lmadi.")


@dp.callback_query(F.data.regexp(r"^admin:service:toggle:\d+$"))
async def admin_service_toggle(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    service_id = int(callback.data.rsplit(":", 1)[1])
    service = None
    for org_id, org_name, org_active in await db.get_all_organizations():
        for sid, name, active in await db.get_all_services(org_id):
            if sid == service_id:
                service = bool(active)
                break
        if service is not None:
            break
    if service is None:
        await callback.answer("Xizmat topilmadi.", show_alert=True)
        return
    ok = await db.set_service_active(service_id, not service)
    await callback.answer("Holat yangilandi." if ok else "Amal bajarilmadi.")


@dp.callback_query(F.data.regexp(r"^admin:service:delete:\d+$"))
async def admin_service_delete(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    service_id = int(callback.data.rsplit(":", 1)[1])
    ok = await db.delete_service(service_id)
    await callback.answer(
        "Xizmat o‘chirildi." if ok else
        "O‘chirilmadi: navbatlar tarixi mavjud yoki xizmat topilmadi.",
        show_alert=not ok,
    )


@dp.callback_query(F.data == "admin:skip")
async def admin_skip_current(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    queues = await db.get_waiting_and_called_queues()
    current = next((q for q in queues if q[2] == "Chaqirildi"), None)
    if not current:
        await callback.answer("O‘tkaziladigan chaqirilgan navbat yo‘q.", show_alert=True)
        return
    await do_skip_queue(callback, bot, current[0])


@dp.callback_query(F.data.regexp(r"^admin:skip:\d+$"))
async def admin_skip_specific(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    await do_skip_queue(callback, bot, int(callback.data.rsplit(":", 1)[1]))


async def do_skip_queue(callback: CallbackQuery, bot: Bot, queue_id: int):
    queue = await db.get_queue_by_id(queue_id)
    if not queue or not await db.skip_queue(queue_id):
        await callback.answer("Navbatni o‘tkazib bo‘lmadi.", show_alert=True)
        return
    user_id, number, org_name, service_name = queue
    try:
        await bot.send_message(
            user_id,
            f"⏭ <b>{number}</b> navbatingiz vaqtincha o‘tkazildi.\n"
            "Iltimos, navbat holatini botdan tekshiring.",
        )
    except Exception:
        logger.warning("User %s ga o‘tkazish xabari yuborilmadi", user_id)
    await callback.answer("Navbat o‘tkazildi.")
    await callback.message.answer(f"⏭ {number} navbat qayta kutish holatiga o‘tkazildi.")


@dp.callback_query(F.data.regexp(r"^admin:call:\d+$"))
async def admin_call_specific(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        await callback.answer("Ruxsat yo‘q.", show_alert=True)
        return
    queue_id = int(callback.data.rsplit(":", 1)[1])
    queue = await db.get_queue_by_id(queue_id)
    if not queue:
        await callback.answer("Navbat topilmadi.", show_alert=True)
        return
    async with aiosqlite.connect(db.DB_PATH) as conn:
        cur = await conn.execute(
            "UPDATE queues SET status='called', updated_at=? WHERE id=? AND status='waiting'",
            (db.now_text(), queue_id),
        )
        await conn.commit()
    if cur.rowcount == 0:
        await callback.answer("Navbat kutilayotgan holatda emas.", show_alert=True)
        return
    user_id, number, org_name, service_name = queue
    try:
        await bot.send_message(
            user_id,
            f"📣 <b>Navbatingiz keldi!</b>\n🎫 {number}\n🏢 {org_name}\n📌 {service_name}",
        )
    except Exception:
        logger.warning("User %s ga navbat xabari yuborilmadi", user_id)
    await callback.answer("Navbat chaqirildi.")
    await callback.message.answer(f"📣 {number} navbat chaqirildi.")



async def main():
    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN topilmadi. Loyiha papkasidagi .env faylini yarating "
            "va BOT_TOKEN qiymatini kiriting. .env.example faylini ko‘ring."
        )
    if not ADMIN_IDS:
        logger.warning("ADMIN_IDS kiritilmagan. /admin ishlamaydi.")

    await db.init_db()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        me = await bot.get_me()
        logger.info("Bot ishga tushmoqda: @%s", me.username)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
