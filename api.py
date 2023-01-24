import pandas as pd
import requests

headers = {
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-Mode": "no-cors",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9"
}


def get_from_json(path: str) -> pd.DataFrame:
    res = pd.read_json(path)
    res = pd.json_normalize(res)
    return res


def get_from_excel(path: str, sheet_name: str = 'Sheet1') -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name)


def get_from_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


def get_http_data(url: str) -> pd.DataFrame:
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        try:
            if 'records' in res.json().keys():
                res = pd.json_normalize(res.json()['records'])
            else:
                res = pd.json_normalize(res.json())
            return res
        except AttributeError:
            return pd.json_normalize(res.json())
    else:
        print(res)
        return pd.DataFrame()


