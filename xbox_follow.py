import threading
import requests

from my_xbox import Client


class AddFriend:
    def __init__(self):
        self.accounts = self.get_accounts()

    @staticmethod
    def get_accounts():
        with open('accounts.txt') as file:
            accounts = file.read().split('\n')
            accounts = [ac.split(':') for ac in accounts if ac != '']
            return accounts

    def get_account(self):
        try:
            return self.accounts.pop(0)
        except:
            return None

    @staticmethod
    def add_friend(user_xuid, friend_xuid, token):
        url = f'https://social.xboxlive.com/users/xuid({user_xuid})/people/xuids?method=add'
        headers = {
            'Authorization': token,
            'Accept-Charset': 'UTF-8',
            'x-xbl-contract-version': '2',
            'Accept': 'application/json',
            'Content-Type': "application/json",
            'Host': 'social.xboxlive.com',
            'Expect': '100-continue',
            'Connection': 'Keep-Alive',
        }
        payload = {
            'xuids': [friend_xuid]
        }
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200 or res.status_code == 204:
            return True
        else:
            return res.status_code

    def multi_add(self):
        client = Client()
        while True:
            client.session = requests.session()
            account = self.get_account()
            if not account:
                break

            msg = ''
            email = account[0]
            password = account[1]

            msg += f'adding {friend_xuid} to {email}\nlogging in\n'

            try:
                client.authenticate(email, password)
                msg += 'logged in\n'
            except:
                msg += f'couldn\'t log in to {email}\n'
                msg += '=' * 55
                msg += '\n'

                with print_lock:
                    print(msg)
                continue

            token = client.token_16hr
            user_xuid = client.user_xid

            msg += f'adding as friend\n'

            added = self.add_friend(user_xuid, friend_xuid, token)
            if added is True:
                msg += 'added\n'
            else:
                msg += f'couldn\'t add as friend. [ststus code: {added}]'

            msg += '=' * 55
            msg += '\n'
            with print_lock:
                print(msg)


if __name__ == '__main__':
    print_lock = threading.Lock()
    friend_xuid = input('enter xuid to add: ')
    add_friend = AddFriend()
    threads = [threading.Thread(target=add_friend.multi_add) for _ in range(25)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()
#