
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def main_menu(is_admin: bool = False):
    rows = [
        [
            KeyboardButton(text="🎫 Navbat olish"),
            KeyboardButton(text="📋 Navbatim"),
        ],
        [
            KeyboardButton(text="❌ Navbatni bekor qilish"),
            KeyboardButton(text="📞 Aloqa"),
        ],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="👨‍💻 Admin panel")])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Bo‘limni tanlang...",
    )


def back_to_main(is_admin: bool = False):
    return main_menu(is_admin)


def organizations_keyboard(organizations):
    rows = [
        [InlineKeyboardButton(
            text=f"🏢 {name}",
            callback_data=f"org:{org_id}",
        )]
        for org_id, name in organizations
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def services_keyboard(services, org_id: int):
    rows = [
        [InlineKeyboardButton(
            text=f"📌 {name}",
            callback_data=f"service:{org_id}:{service_id}",
        )]
        for service_id, name in services
    ]
    rows.append([
        InlineKeyboardButton(
            text="⬅️ Tashkilotlarga qaytish",
            callback_data="nav:back_orgs",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📣 Keyingi navbat",
                callback_data="admin:next",
            )
        ],
        [
            InlineKeyboardButton(
                text="⏭ Navbatni o‘tkazish",
                callback_data="admin:skip",
            )
        ],
        [
            InlineKeyboardButton(
                text="🏢 Tashkilotlar",
                callback_data="admin:organizations",
            )
        ],
        [
            InlineKeyboardButton(
                text="📌 Xizmatlar",
                callback_data="admin:services",
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Statistikani yangilash",
                callback_data="admin:refresh",
            )
        ],
    ])


def admin_organizations_keyboard(organizations):
    rows = [
        [
            InlineKeyboardButton(
                text=f"🏢 {name}",
                callback_data=f"admin:org:{org_id}",
            )
        ]
        for org_id, name in organizations
    ]
    rows.append([
        InlineKeyboardButton(
            text="➕ Tashkilot qo‘shish",
            callback_data="admin:org:add",
        )
    ])
    rows.append([
        InlineKeyboardButton(
            text="⬅️ Admin panel",
            callback_data="admin:home",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_organization_actions(org_id: int, is_active: bool = True):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✏️ Nomini o‘zgartirish",
                callback_data=f"admin:org:rename:{org_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="🔴 Faolsizlantirish" if is_active else "🟢 Faollashtirish",
                callback_data=f"admin:org:toggle:{org_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑 O‘chirish",
                callback_data=f"admin:org:delete:{org_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Tashkilotlar",
                callback_data="admin:organizations",
            )
        ],
    ])


def admin_services_keyboard(organizations):
    rows = [
        [
            InlineKeyboardButton(
                text=f"🏢 {name}",
                callback_data=f"admin:services:org:{org_id}",
            )
        ]
        for org_id, name in organizations
    ]
    rows.append([
        InlineKeyboardButton(
            text="⬅️ Admin panel",
            callback_data="admin:home",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_service_list_keyboard(services, org_id: int):
    rows = [
        [
            InlineKeyboardButton(
                text=f"📌 {name}",
                callback_data=f"admin:service:{service_id}",
            )
        ]
        for service_id, name in services
    ]
    rows.append([
        InlineKeyboardButton(
            text="➕ Xizmat qo‘shish",
            callback_data=f"admin:service:add:{org_id}",
        )
    ])
    rows.append([
        InlineKeyboardButton(
            text="⬅️ Tashkilotlar",
            callback_data="admin:services",
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_service_actions(service_id: int, is_active: bool = True):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✏️ Nomini o‘zgartirish",
                callback_data=f"admin:service:rename:{service_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="🔴 Faolsizlantirish" if is_active else "🟢 Faollashtirish",
                callback_data=f"admin:service:toggle:{service_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑 O‘chirish",
                callback_data=f"admin:service:delete:{service_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Xizmatlar",
                callback_data="admin:services",
            )
        ],
    ])


def queue_actions_keyboard(queue_id: int, status: str):
    buttons = []

    if status in ("Kutilmoqda", "waiting"):
        buttons.append(InlineKeyboardButton(
            text="📣 Chaqirish",
            callback_data=f"admin:call:{queue_id}",
        ))
        buttons.append(InlineKeyboardButton(
            text="⏭ O‘tkazish",
            callback_data=f"admin:skip:{queue_id}",
        ))

    if status in ("Kutilmoqda", "waiting", "Chaqirildi", "called"):
        buttons.append(InlineKeyboardButton(
            text="✅ Yakunlash",
            callback_data=f"admin:finish:{queue_id}",
        ))
        buttons.append(InlineKeyboardButton(
            text="❌ Bekor qilish",
            callback_data=f"admin:cancel:{queue_id}",
        ))

    return InlineKeyboardMarkup(
        inline_keyboard=[[button] for button in buttons]
    )
