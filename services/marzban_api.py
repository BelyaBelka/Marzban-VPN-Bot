from config import MARZBAN_USER, MARZBAN_PASS, MARZBAN_API_URL, SSH_USERNAME, SSH_HOST, SSH_PASSWORD, token_pay
from marzban import MarzbanAPI, UserTemplateCreate, UserCreate, ProxySettings, UserModify
from db import save_user_link, remove_user_link, get_vpn_username, get_all_user_links
from datetime import datetime, timedelta
from yoomoney import Client, Quickpay
import httpx
import uuid
import asyncio
import logging

api = MarzbanAPI(
    base_url=MARZBAN_API_URL,
    ssh_username=SSH_USERNAME,
    ssh_host=SSH_HOST,
    ssh_port=22,
    ssh_password=SSH_PASSWORD
)

template_id = None


class MarzbanTokenCache:
    def __init__(self, client: MarzbanAPI,
                 username: str, password: str,
                 token_expire_minutes: int = 1440):
        self._client = client
        self._username = username
        self._password = password
        self._token_expire_minutes = token_expire_minutes
        self._token: str = None
        self._exp_at: datetime = None

    async def get_token(self):
        if not self._exp_at or self._exp_at < datetime.now():
            logging.info(f'Получение нового токена')
            self._token = await self.get_new_token()
            self._exp_at = datetime.now() + timedelta(minutes=self._token_expire_minutes - 1)
        return self._token

    async def get_new_token(self):
        try:
            token = await self._client.get_token(
                username=self._username,
                password=self._password
            )
            return token.access_token
        except Exception as e:
            logging.error(f'Ошибка получения токена: {e}', exc_info=True)
            raise e


token_cache = MarzbanTokenCache(
    client=api,
    username=MARZBAN_USER,
    password=MARZBAN_PASS,
    token_expire_minutes=1440
)

async def get_marzban_token():
    try:
        return await token_cache.get_token()
    except Exception as e:
        raise Exception(f"❗ Ошибка получения токена: {str(e)}")

async def create_template() -> tuple[int, int]:
    try:
        token = await get_marzban_token()
        templates = await api.get_user_templates(token=token, offset=0, limit=100)

        template1 = next((t for t in templates if t.name == "Month"), None)
        default_template = next((t for t in templates if t.name == "Default"), None)

        if not template1:
            template1_payload = UserTemplateCreate(
            name="Month",
            data_limit=1073741824000,
            expire_duration=2592000,
            username_prefix="user_",
            username_suffix="template"
            )
            template1 = await api.add_user_template(template=template1_payload, token=token)

        if not default_template:
            default_payload = UserTemplateCreate(
                name="Default",
                data_limit=0,
                expire_duration=0,
                username_prefix="user_",
                username_suffix="default"
            )
            default_template = await api.add_user_template(template=default_payload, token=token)

        return template1.id, default_template.id

    except Exception as e:
        raise Exception(f"Ошибка создания шаблона: {str(e)}")

async def create_user_admin(username: str, telegram_id: int) -> str:
    token = await get_marzban_token()
    await create_template()
    try:
        user_info = await api.get_user(username=username, token=token)
        return f"⚠️ Пользователь {username} уже существует"
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            raise e

        templates = await api.get_user_templates(token=token, offset=0, limit=100)
        month_days_template = next((t for t in templates if t.name == "Month"), None)

        if month_days_template is None:
            return "⚠️ Шаблон с месячным сроком действия не найден"


        expire_date = int((datetime.utcnow() + timedelta(seconds=month_days_template.expire_duration)).timestamp())

        user_payload = UserCreate(
            username=username,
            template_id=month_days_template.id,
            proxies={
                "vless": ProxySettings(id=None, flow="xtls-rprx-vision")
            },
            data_limit=month_days_template.data_limit,
            expire=expire_date
        )

        added_user = await api.add_user(user=user_payload, token=token)
        user_subscription_info = await api.get_user_subscription_info(url=added_user.subscription_url)

        save_user_link(telegram_id, username)

        return f"✅ Пользователь создан: `{username}`\nКлюч: {user_subscription_info.links}"


async def delete_user_admin(username: str) -> str:
    token = await get_marzban_token()

    try:
        await api.remove_user(username=username, token=token)
        remove_user_link(username)
        return f"✅ пользователь {username} удалён"

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"❌ Ошибка!Пользователя с данным никнейном не существует"
        else:
            return f"⚠️ Произошла ошибка: {e.response.status_code}, обратитесь в техническую поддержку"

    except Exception as e:
        return f"⚠️ Ошибка при удалении пользователя {str(e)}"


async def admin_status(username: str) -> str:
    token = await get_marzban_token()

    try:
        user_info = await api.get_user(username=username, token=token)

        timestamp = user_info.expire
        if timestamp is not None:
            date = datetime.utcfromtimestamp(timestamp)
            expire_str = date.strftime("%d.%m.%Y %H:%M (UTC)")
        else:
            expire_str = "безлимит"

        user_subscription_info = await api.get_user_subscription_info(url=user_info.subscription_url)
        return f"Информация по пользователю {user_info.username}:\nИстекает: {expire_str}\nЛимит данных: {user_info.data_limit}\nСтатус лицензии: {user_info.status}\nКлюч пользователя: {user_subscription_info.links}"

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"❌ Ошибка!Пользователя с данным никнейном не существует"
        else:
            return f"⚠️ Произошла ошибка: {e.response.status_code}, обратитесь в техническую поддержку"

async def print_list_users(page=1, per_page=30) -> str:
    token = await get_marzban_token()

    try:
        users_info = await api.get_users(token=token, offset=0, limit=1)
        total_users = users_info.total

        if total_users == 0:
            return f"❗️ Список пользователей пуст"

        offset = (page - 1) * per_page

        users = await api.get_users(token=token, offset=offset, limit=per_page)

        total_pages = (total_users + per_page - 1) // per_page

        if not users.users and total_users > 0:
            return f"❌ Страница {page} не существует. Всего страниц: {total_pages}"

        user_list = [user.username for user in users.users]
        formatted_list = "\n".join([f"{offset + i + 1}. {username}" for i, username in enumerate(user_list)])
        return f"Список пользователей (страница {page}/{total_pages}):\n{formatted_list}\n\nВсего пользователей: {total_users}\nДля просмотра другой страницы используйте: /list_users <номер_страницы>"


    except Exception as e:
        return f"❌ Ошибка получения списка пользователей: {str(e)}"

async def extension_subscription(username: str, days=30) -> str:
    token = await get_marzban_token()

    try:
        user = await api.get_user(username=username, token=token)

        now = datetime.utcnow()

        if user.expire:
            current_expire = datetime.utcfromtimestamp(user.expire)
            base_date = current_expire if current_expire > now else now
        else:
            base_date = now

        new_expire = base_date + timedelta(days=days)
        new_expire_ts = int(new_expire.timestamp())

        await api.modify_user(username=username,
                              user=UserModify(expire=new_expire_ts),
                              token=token)

        return f"Подписка пользователя {username} продлена до {new_expire.strftime('%d.%m.%Y %H:%M')} UTC"

    except Exception as e:
        return f"Ошибка при продлении: {str(e)}"

#---------------------------------------------------------------------------------------------------
#                                         ИНТЕРФЕЙС ПОЛЬЗОВАТЕЛЯ
#---------------------------------------------------------------------------------------------------
ACTIVE_PAYMENTS = {}
async def create_user_user(username: str, telegram_id: int):
    token = await get_marzban_token()
    try:
        linked_username = get_vpn_username(telegram_id)
        if linked_username:
            return f"⛔️ У вас уже есть зарегистрированный VPN-аккаунт: {linked_username}"

        try:
            user_info = await api.get_user(username=username, token=token)
            return f"⛔️ Пользователь {username} уже существует"
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                raise e

        templates = await api.get_user_templates(token=token, offset=0, limit=100)
        zero_days_template = next((t for t in templates if t.name == "Default"), None)

        if zero_days_template is None:
            return f"⛔️ Шаблон не найден!"

        expire_date = int((datetime.utcnow() + timedelta(seconds=zero_days_template.expire_duration)).timestamp())

        user_payload = UserCreate(
            username=username,
            template_id=zero_days_template.id,
            proxies={
                "vless": ProxySettings(id=None, flow="xtls-rprx-vision")
            },
            data_limit=zero_days_template.data_limit,
            expire=expire_date
        )

        added_user = await api.add_user(user=user_payload, token=token)
        user_subscription_info = await api.get_user_subscription_info(url=added_user.subscription_url)

        save_user_link(telegram_id, username)

        return f"✅ Пользователь создан: `{username}`\nКлюч: {user_subscription_info.links}"

    except Exception as e:
        return f"❌ Ошибка создания пользователя: {str(e)}"


async def status_user(username: str, telegram_id: int) -> str:
    token = await get_marzban_token()

    try:
        linked_username = get_vpn_username(telegram_id)

        if linked_username != username:
            return "⛔️ У вас нет доступа к этой информации"

        user_info = await api.get_user(username=username, token=token)

        timestamp = user_info.expire
        if timestamp is not None:
            date = datetime.utcfromtimestamp(int(timestamp))
            expire_str = date.strftime("%d.%m.%Y %H:%M (UTC)")
        else:
            expire_str = "Не указано"
        return f"Информация по пользователю {user_info.username}:\nИстекает: {expire_str}\nЛимит данных: {user_info.data_limit}\nСтатус лицензии: {user_info.status}"

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"❌ Ошибка!Пользователя с данным никнейном не существует"
        else:
            return f"❌ Произошла ошибка: {e.response.status_code}, обратитесь в техническую поддержку"


async def fetch_all_user_links():
    links = get_all_user_links()
    if not links:
        return f"❌ В базе данных нет ни одной связки."

    result = ["Список связок:"]
    for tg_id, vpn_username in links:
        result.append(f"{vpn_username} — {tg_id}")
    return "\n".join(result)


async def generate_payment_link(username: str, user_id: int) -> tuple[str, str]:
    if user_id in ACTIVE_PAYMENTS:
        return "⛔️ У вас уже есть активный платёж", None

    label = uuid.uuid4().hex
    ACTIVE_PAYMENTS[user_id] = label

    quickpay = Quickpay(
        receiver="4100119130087412",
        quickpay_form="shop",
        targets="Sponsor this project",
        paymentType="SB",
        sum=100,
        label=label
    )

    return f"Для оплаты перейдите по ссылке: {quickpay.redirected_url}", label

async def check_payment_and_extend(username: str, label: str, user_id: int) -> str:
    client = Client(token_pay)

    try:
        for _ in range(60):
            history = client.operation_history(label=label)
            for op in history.operations:
                if op.label == label and op.status == "success":
                    token = await get_marzban_token()
                    user = await api.get_user(username=username, token=token)

                    now = datetime.utcnow()
                    base = datetime.utcfromtimestamp(user.expire) if user.expire else now
                    base = max(base, now)

                    new_expire = base + timedelta(days=30)
                    new_expire_ts = int(new_expire.timestamp())

                    await api.modify_user(
                        username=username,
                        user=UserModify(expire=new_expire_ts),
                        token=token
                    )

                    return f"✅ Подписка {username} продлена до {new_expire.strftime('%d.%m.%Y %H:%M')} UTC"

            await asyncio.sleep(10)

    except Exception as e:
        return f"⚠️ Ошибка при проверке платежа: {str(e)}"

    finally:
        ACTIVE_PAYMENTS.pop(user_id, None)

    return "⏳ Время ожидания оплаты истекло. Попробуйте снова."

