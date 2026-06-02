import requests
import logging

import os
from abc import ABC, abstractmethod
import urllib.parse

from core import settings

logger = logging.getLogger(__name__)

class BaseTicketingService(ABC):
    """
    هر سیستم تیکتینگی (زمد، جیرا، زِندسک) که در آینده اضافه شود، باید این متدها را داشته باشد.
    """

    @abstractmethod
    def get_or_create_user(self, identifier, **kwargs): pass

    @abstractmethod
    def create_ticket(self, title, identifier, message_body, **kwargs): pass

    @abstractmethod
    def get_customer_history(self, identifier): pass

    @abstractmethod
    def get_ticket_articles(self, ticket_id): pass

    @abstractmethod
    def add_ticket_note(self, ticket_id, body): pass

    @abstractmethod
    def get_all_tickets(self, limit=20): pass

    @abstractmethod
    def get_open_tickets(self): pass

    @abstractmethod
    def update_ticket_state(self, ticket_id, status): pass

    @abstractmethod
    def update_ticket_group(self, ticket_id, target_group, by_user): pass

    @abstractmethod
    def get_groups(self): pass

    @abstractmethod
    def create_group(self, name, note=""): pass

    @abstractmethod
    def sync_group(self,name,is_active): pass

    @abstractmethod
    def get_paginated_tickets(self,query_string,page,per_page): pass

    @abstractmethod
    def update_ticket_owner(self, ticket_id, owner_email): pass

    @abstractmethod
    def assign_user_to_group(self,user_email, group_name, action): pass

class ZammadService:
    def __init__(self):
        self.base_url = settings.ZAMMAD_API_URL
        self.token = settings.ZAMMAD_API_TOKEN

        self.headers = {
            "Authorization": f"Token token={self.token}",
            "Content-Type": "application/json"
        }

    def _detect_id_type(self, identifier):
        if len(identifier) == 11 and identifier.startswith("09"):
            return "mobile"
        elif len(identifier) == 10 and identifier.isdigit():
            return "national_id"
        return "unknown"

    def get_or_create_user(self, identifier, firstname="کاربر", lastname="مهمان", mobile=None, national_id=None, role='Customer'):
        id_type = self._detect_id_type(identifier)

        is_email = '@' in identifier
        final_email = identifier if is_email else f"{identifier}@crm.local"

        if is_email:
            search_query = f"email:\"{identifier}\""
        else:
            search_query = f"email:\"{identifier}@crm.local\" OR login:\"{identifier}\" OR mobile:*{identifier}* OR national_id:\"{identifier}\""

        search_url = f"{self.base_url}/users/search?query={search_query}"



        try:
            search_res = requests.get(search_url, headers=self.headers)
            search_res.raise_for_status()
            users = search_res.json()

            if users:
                user_id = users[0]['id']
                existing_roles = users[0].get('roles',[])
                if role not in existing_roles:
                    update_payload = {"roles": [role]}
                    try:
                        requests.put(f"{self.base_url}/users/{user_id}", json=update_payload, headers=self.headers)
                        logger.info(f"✅ User {identifier} role updated to {role} in Zammad.")
                    except requests.exceptions.RequestException as e:
                        logger.error(f"❌ Failed to update role for user {identifier}: {e}")

                return user_id

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Zammad API Error (Search User): {str(e)}")

        create_url = f"{self.base_url}/users"
        payload = {
            "firstname": firstname,
            "lastname": lastname,
            "email": final_email,
            "login": identifier,
            "roles": [role],
        }

        if mobile:
            payload["mobile"] = mobile
        elif id_type == "mobile":
            payload["mobile"] = identifier

        if national_id:
            payload["national_id"] = national_id
        elif id_type == "national_id":
            payload["national_id"] = identifier


        try:
            create_res = requests.post(create_url, json=payload, headers=self.headers)
            create_res.raise_for_status()

            new_user = create_res.json()
            return new_user['id']

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network Error Creating User: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Zammad Response: {e.response.text}")
            return None

    def create_ticket(self, title, identifier, message_body, firstname="کاربر", lastname="مهمان", mobile=None, national_id=None, group="Users", owner=None):

        customer_id = self.get_or_create_user(
            identifier=identifier,
            firstname=firstname,
            lastname=lastname,
            mobile=mobile,
            national_id=national_id
        )

        if not customer_id:
            logger.error("❌ CANNOT CREATE TICKET: NO CUSTOMER ID RETURNED")
            return None

        endpoint = f"{self.base_url}/tickets"
        payload = {
            "title": title,
            "group": group,
            "customer_id": customer_id,
            "article": {
                "subject": title,
                "body": message_body,
                "type": "note",
                "internal": False
            }
        }

        if owner:
            payload['owner'] = owner

        try:
            response = requests.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Zammad API Error (Create Ticket): {str(e)}")
            return None

    def get_customer_history(self, identifier):
        res_codes = self.get_resolution_codes()
        res_map = {item['code']: item['title'] for item in res_codes}

        NON_REOPENABLE_CODES = ['resolved_fl', 'duplicate']

        search_query = f"mobile:{identifier} OR national_id:{identifier}"
        search_user_url = f"{self.base_url}/users/search?query={search_query}"

        try:
            user_res = requests.get(search_user_url, headers=self.headers)
            user_res.raise_for_status()
            users = user_res.json()

            if not users:
                return []

            user_id = users[0]['id']

            tickets_url = f"{self.base_url}/tickets/search?query=customer_id:{user_id}&expand=true"
            tickets_res = requests.get(tickets_url, headers=self.headers)
            tickets_res.raise_for_status()

            raw_tickets = tickets_res.json()
            clean_tickets = []

            if isinstance(raw_tickets, list):
                for t in raw_tickets:
                    state = t.get("state")
                    res_code = t.get("resolution_code")

                    clean_tickets.append({
                        "id": t.get("id"),
                        "title": t.get("title"),
                        "state": "open" if state in ["open", "new"] else "closed",
                        "created_at": t.get("created_at"),
                        "updated_at": t.get("updated_at"),
                        "is_reopenable": False if (state == "closed" and res_code in NON_REOPENABLE_CODES) else True,
                        "resolution": res_map.get(res_code, "مختومه") if state == "closed" else ""
                    })
            return clean_tickets

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error Fetching Customer History: {str(e)}")
            return []


    def get_ticket_articles(self, ticket_id):
        endpoint = f"{self.base_url}/ticket_articles/by_ticket/{ticket_id}"
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()

            articles = response.json()
            clean_articles = []
            for art in articles:
                clean_articles.append({
                    "id": art.get("id"),
                    "from": art.get("from"),
                    "body": art.get("body"),
                    "type": art.get("type"),
                    "internal": art.get("internal"),
                    "created_at": art.get("created_at")
                })
            return clean_articles
        except Exception as e:
            logger.error(f"❌ Error Fetching Articles for ticket {ticket_id}: {e}")
            return []

    def add_ticket_note(self, ticket_id, body):
        endpoint = f"{self.base_url}/ticket_articles"
        payload = {
            "ticket_id": ticket_id,
            "subject": "گزارش کارشناس",
            "body": body,
            "type": "note",
            "internal": True,
            "content_type": "text/plain"
        }
        try:
            response = requests.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network Error Adding Note: {e}")
            if 'response' in locals():
                logger.error(f"❌ Response details: {response.text}")
            return None

    def sync_admin_user(self, email, firstname, lastname, roles):
        if not email:
            email = f"{lastname}@crm.local"

        payload = {
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "roles": roles,
            "active": True
        }

        search_url = f"{self.base_url}/users/search?query=email:{email}"
        try:
            res = requests.get(search_url, headers=self.headers)
            res.raise_for_status()
            users = res.json()

            if users:
                user_id = users[0]['id']
                requests.put(f"{self.base_url}/users/{user_id}", json=payload, headers=self.headers)
            else:
                requests.post(f"{self.base_url}/users", json=payload, headers=self.headers)
        except Exception as e:
            logger.error(f"❌ Error Syncing Admin to Zammad: {e}")

    def get_all_tickets(self, limit=50):
        search_url = f"{self.base_url}/tickets/search?query=id:*&sort_by=created_at&order_by=desc&limit={limit}&expand=true"

        try:
            res = requests.get(search_url, headers=self.headers)
            res.raise_for_status()
            raw_tickets = res.json()

            clean_tickets = []
            if isinstance(raw_tickets, list):
                for t in raw_tickets:
                    customer_name = "نامشخص"

                    # 🌟 دیباگ: چک کردن نوع دیتای برگشتی از Zammad
                    customer_data = t.get("customer")

                    if isinstance(customer_data, dict):
                        fname = customer_data.get('firstname', '').strip()
                        lname = customer_data.get('lastname', '').strip()

                        if fname or lname:
                            full_name = f"{fname} {lname}".strip()
                            if "@crm.local" not in full_name:
                                customer_name = full_name
                            else:
                                customer_name = full_name.split('@')[0]
                        else:
                            customer_name = customer_data.get('login', 'نامشخص')
                            if "@crm.local" in customer_name:
                                customer_name = customer_name.split('@')[0]
                    elif isinstance(customer_data, str):
                        if "@crm.local" in customer_data:
                            customer_name = customer_data.split('@')[0]
                        else:
                            customer_name = customer_data

                    clean_tickets.append({
                        "id": t.get("id"),
                        "title": t.get("title"),
                        "state": t.get("state"),
                        "customer": customer_name,
                        "created_at": t.get("created_at", ""),
                    })
            return clean_tickets
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error Fetching All Tickets: {str(e)}")
            return []

    def get_open_tickets(self):
        """
        گرفتن لیست تیکت‌های باز و جدید از Zammad برای نمایش در جدول داشبورد
        """
        # کوئری برای گرفتن تیکت‌هایی که وضعیتشون باز یا جدید هست
        search_url = f"{self.base_url}/tickets/search?query=state:(new OR open)&expand=true"

        try:
            res = requests.get(search_url, headers=self.headers)
            res.raise_for_status()
            raw_tickets = res.json()

            clean_tickets = []
            if isinstance(raw_tickets, list):
                for t in raw_tickets:
                    created_at = t.get("created_at", "")

                    # استخراج دیتای تمیز برای فرانت‌اِند
                    clean_tickets.append({
                        "id": t.get("id"),
                        "title": t.get("title"),
                        # فعلا آیدی مشتری رو میذاریم تا بعدا اسمش رو از دیتابیس خودت مچ کنی
                        "customer": f"مشتری {t.get('customer_id')}",
                        "state": "open" if t.get("state") in ["open", "new"] else "closed",
                        "date": created_at[:10] if created_at else "",
                        "time": created_at[11:16] if created_at else ""
                    })
            return clean_tickets
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error Fetching Tickets List: {str(e)}")
            return []

    def update_ticket_state(self, ticket_id, state, resolution_code=None):
        """
        تغییر وضعیت تیکت + ثبت کد خاتمه در فیلد سفارشی زمد
        """
        endpoint = f"{self.base_url}/tickets/{ticket_id}"
        payload = {
            "state": state
        }

        if state == 'closed' and resolution_code:
            payload["resolution_code"] = resolution_code
        elif state == 'open':
            payload["resolution_code"] = None

        try:
            response = requests.put(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error Updating Ticket State: {str(e)}")
            return False

    def update_ticket_group(self, ticket_id, target_group, by_user='سیستم'):

        endpoint = f"{self.base_url}/tickets/{ticket_id}"
        payload = {
            "group": target_group,
            'owner_id': 1
        }

        try:
            response = requests.put(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()

            system_message = f" این درخواست توسط «{by_user}» به کارتابل تیم «{target_group}» ارجاع داده شد و هم‌اکنون منتظر تخصیص کارشناس جدید است."
            self.add_ticket_note(ticket_id, system_message)

            logger.info(f"✅ Ticket {ticket_id} group updated to {target_group} in Zammad.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error Updating Ticket Group to {target_group}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Zammad Response: {e.response.text}")
            return False

    def get_groups(self):

        endpoint = f"{self.base_url}/groups"
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()

            raw_groups = response.json()
            clean_groups = []

            for group in raw_groups:
                if group.get("active"):
                    clean_groups.append({
                        "id": group.get("id"),
                        "name": group.get("name"),
                        "note": group.get("note",""),
                    })
            return clean_groups
        except requests.exceptions.RequestException as e:
            logger.error(f"Error Fetching Zammad Groups: {str(e)}")
            return []

    def create_group(self, name):
        return self.sync_group(name, True)

    #     endpoint = f"{self.base_url}/groups"
    #     payload = {
    #         "name": name,
    #         "note": note,
    #         'active': True,
    #     }
    #
    #     try:
    #         response = requests.post(endpoint, json=payload, headers=self.headers)
    #         response.raise_for_status()
    #         new_group = response.json()
    #
    #         return {
    #             "id": new_group.get("id"),
    #             "name": new_group.get("name"),
    #         }
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"Error Creating Zammad Group: {str(e)}")
    #         return None
    #
    # def add_ticket_tags(self, ticket_id, tag_item):
    #     endpoint = f"{self.base_url}/tags/add"
    #     payload = {
    #         "object": "Ticket",
    #         "o_id": ticket_id,
    #         "item": tag_item,
    #     }
    #     try:
    #         response = requests.post(endpoint, json=payload, headers=self.headers)
    #         response.raise_for_status()
    #         return True
    #     except requests.exceptions.RequestException as e:
    #         logger.error(f"Error Adding Tag to Ticket {ticket_id}: {str(e)}")
    #         return False

    def remove_ticket_tags(self, ticket_id, tag_item):
        endpoint = f"{self.base_url}/tags/remove"
        payload = {
            "object": "Ticket",
            "o_id": ticket_id,
            "item": tag_item,
        }
        try:
            response = requests.post(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            return False

    def get_resolution_codes(self):
        endpoint = f"{self.base_url}/object_manager_attributes"
        try:
            res = requests.get(endpoint, headers=self.headers)
            res.raise_for_status()
            attributes = res.json()

            for attr in attributes:
                if attr.get('name') == 'resolution_code':
                    options = attr.get('data_option', {}).get('options', {})
                    clean_options = []

                    if isinstance(options, dict):
                        for key, label in options.items():
                            clean_options.append({"code": key, "title": label})

                    elif isinstance(options, list):
                        for item in options:
                            if isinstance(item, dict):
                                clean_options.append({
                                    "code": item.get('value', ''),
                                    "title": item.get('display', item.get('name', ''))
                                })
                            elif isinstance(item, str):
                                clean_options.append({"code": item, "title": item})

                    return clean_options

            return []

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error Fetching Resolution Codes from Zammad: {str(e)}")
            return []

    def sync_group(self,name,is_active):
        payload = {
            "name": name,
            "active": is_active,
            'note': "Created/Updated via Django Crm Sync"
        }

        try:
            endpoint = f"{self.base_url}/groups"
            res = requests.get(endpoint, headers=self.headers)
            res.raise_for_status()
            all_groups = res.json()

            existing_group = next((g for g in all_groups if g.get("name") == name), None)

            if existing_group:
                group_id = existing_group["id"]
                update_url = f"{self.base_url}/groups/{group_id}"

                update_res = requests.put(update_url, json=payload, headers=self.headers)
                update_res.raise_for_status()

                logger.info(f"✅ گروه '{name}' در زمد با موفقیت آپدیت شد.")
                return update_res.json()

            else:
                create_res = requests.post(endpoint, json=payload, headers=self.headers)
                create_res.raise_for_status()

                logger.info(f"✅ گروه '{name}' در زمد با موفقیت ساخته شد.")
                return create_res.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ خطا در همگام‌سازی گروه '{name}' با زمد: {str(e)}")
            return None

    def get_paginated_tickets(self, query_string="id:*", page=1, per_page=10):
        encoded_query = urllib.parse.quote(query_string)
        search_url = f"{self.base_url}/tickets/search?query={encoded_query}&sort_by=created_at&order_by=desc&expand=true&page={page}&per_page={per_page}"

        try:
            res = requests.get(search_url, headers=self.headers)
            res.raise_for_status()
            raw_tickets = res.json()

            clean_tickets = []
            if isinstance(raw_tickets, list):
                user_ids = set()
                for t in raw_tickets:
                    if t.get("customer_id"):
                        user_ids.add(str(t["customer_id"]))
                    if t.get("owner_id") and str(t["owner_id"]) != "1":
                        user_ids.add(str(t["owner_id"]))

                user_map = {}
                if user_ids:
                    ids_query = " OR ".join(user_ids)
                    users_url = f"{self.base_url}/users/search?query=id:({urllib.parse.quote(ids_query)})"
                    try:
                        u_res = requests.get(users_url, headers=self.headers)
                        if u_res.status_code == 200:
                            for u in u_res.json():
                                user_map[u['id']] = u
                    except Exception as e:
                        logger.error(f"Error fetching users map: {e}")

                for t in raw_tickets:
                    cust_id = t.get("customer_id")
                    own_id = t.get("owner_id")

                    customer_name = "نامشخص"
                    customer_identifier = ""
                    owner_name = "تخصیص نیافته"

                    # -- تنظیم اسم مشتری --
                    if cust_id and cust_id in user_map:
                        u = user_map[cust_id]
                        fname = u.get("firstname", "").strip()
                        lname = u.get("lastname", "").strip()

                        if fname or lname:
                            full_name = f"{fname} {lname}".strip()
                            if full_name == "کاربر مهمان":
                                customer_name = u.get("login", "کاربر مهمان")
                            else:
                                customer_name = full_name
                        else:
                            customer_name = u.get("login", "نامشخص")

                        if "@crm.local" in customer_name:
                            customer_name = customer_name.split('@')[0]

                        customer_identifier = u.get("login", "")
                        if "@crm.local" in customer_identifier:
                            customer_identifier = customer_identifier.replace("@crm.local", "")

                    # -- تنظیم اسم کارشناس (مسئول) --
                    if own_id and own_id in user_map and str(own_id) != "1":
                        u = user_map[own_id]
                        fname = u.get("firstname", "").strip()
                        lname = u.get("lastname", "").strip()
                        if fname or lname:
                            owner_name = f"{fname} {lname}".strip()
                        else:
                            owner_name = u.get("login", "تخصیص نیافته")

                    clean_tickets.append({
                        "id": t.get("id"),
                        "title": t.get("title"),
                        "state": t.get("state"),
                        "customer": customer_name,
                        "customer_identifier": customer_identifier,
                        "owner": owner_name,
                        "created_at": t.get("created_at", ""),
                    })

                total_pages = page + 1 if len(clean_tickets) == per_page else page

                return {
                    "tickets": clean_tickets,
                    "total_pages": total_pages
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error Fetching Paginated Tickets: {str(e)}")
            return {"tickets": [], "total_pages": 1}

    def update_ticket_owner(self, ticket_id, owner_email):
        """
        تخصیص تیکت به یک کارشناس مشخص
        """
        endpoint = f"{self.base_url}/tickets/{ticket_id}"
        payload = {
            "owner": owner_email
        }

        try:
            response = requests.put(endpoint, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.info(f"✅ Ticket {ticket_id} assigned to {owner_email}.")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error Assigning Ticket {ticket_id} to {owner_email}: {str(e)}")
            return False

    def assign_user_to_group(self, user_email, group_name, action="add"):

        try:
            search_url = f"{self.base_url}/users/search?query=email:{user_email}"
            user_res = requests.get(search_url, headers=self.headers)
            user_res.raise_for_status()
            users = user_res.json()
            if not users:
                return False
            user_data = users[0]
            user_id = user_data['id']

            groups = self.get_groups()
            target_group = next((g for g in groups if g['name'] == group_name), None)
            if not target_group:
                return False
            group_id = str(target_group['id'])

            current_groups = user_data.get('group_ids', {})

            if action == "add":
                current_groups[group_id] = ["full"]
            elif action == "remove":
                if group_id in current_groups:
                    del current_groups[group_id]

            update_url = f"{self.base_url}/users/{user_id}"
            requests.put(update_url, json={"group_ids": current_groups}, headers=self.headers)

            logger.info(f"✅ User {user_email} {'added to' if action == 'add' else 'removed from'} group {group_name}.")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error updating user {user_email} groups: {str(e)}")
            return False


def get_ticketing_service() -> BaseTicketingService:
    """
    ویوهای جنگو فقط این تابع را صدا می‌زنند.
    اگر فردا خواستید زمد را با جیرا عوض کنید، فقط کلمه ZammadService را در خط زیر عوض می‌کنید!
    """
    return ZammadService()