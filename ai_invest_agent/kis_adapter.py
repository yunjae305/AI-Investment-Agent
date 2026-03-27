from __future__ import annotations

import os
import time
from dataclasses import dataclass

import requests


DEFAULT_TIMEOUT = 10


@dataclass(frozen=True)
class KisCredentials:
    app_key: str
    app_secret: str
    account_no: str
    product_code: str
    base_url: str
    user_agent: str
    env: str


class KisApiClient:
    def __init__(self, env: str = "demo", timeout: int = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout
        self.credentials = self._load_credentials(env)
        self._token: str | None = None
        self._token_expiry: float = 0.0

    @staticmethod
    def is_configured(env: str = "demo") -> bool:
        prefix = "KIS_PAPER_" if env == "demo" else "KIS_"
        required = [
            f"{prefix}APP_KEY",
            f"{prefix}APP_SECRET",
            f"{prefix}ACCOUNT_NO",
        ]
        return all(bool(os.getenv(name)) for name in required)

    def domestic_price(self, symbol: str, market_code: str = "J") -> dict:
        data = self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            tr_id="FHKST01010100",
            params={
                "FID_COND_MRKT_DIV_CODE": market_code,
                "FID_INPUT_ISCD": symbol,
            },
        )
        output = data.get("output") or {}
        price = _to_float(output.get("stck_prpr"))
        return {
            "symbol": symbol,
            "price": price,
            "name": output.get("hts_kor_isnm") or symbol,
            "raw": output,
        }

    def overseas_price(self, symbol: str, exchange_code: str = "NAS") -> dict:
        data = self._get(
            "/uapi/overseas-price/v1/quotations/price",
            tr_id="HHDFS00000300",
            params={
                "AUTH": "",
                "EXCD": exchange_code,
                "SYMB": symbol,
            },
        )
        output = data.get("output") or {}
        price = _to_float(output.get("last") or output.get("base") or output.get("clos"))
        return {
            "symbol": symbol,
            "price": price,
            "name": output.get("name") or symbol,
            "raw": output,
        }

    def order_domestic(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_type: str = "00",
        exchange_id: str = "KRX",
    ) -> dict:
        tr_id = self._pick_domestic_tr_id(side)
        payload = {
            "CANO": self.credentials.account_no,
            "ACNT_PRDT_CD": self.credentials.product_code,
            "PDNO": symbol,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": _format_price(price),
            "EXCG_ID_DVSN_CD": exchange_id,
            "SLL_TYPE": "" if side == "buy" else "01",
            "CNDT_PRIC": "",
        }
        return self._post(
            "/uapi/domestic-stock/v1/trading/order-cash",
            tr_id=tr_id,
            payload=payload,
        )

    def order_overseas(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        exchange_code: str = "NASD",
        order_type: str = "00",
    ) -> dict:
        tr_id = self._pick_overseas_tr_id(side, exchange_code)
        sell_type = "" if side == "buy" else "00"
        payload = {
            "CANO": self.credentials.account_no,
            "ACNT_PRDT_CD": self.credentials.product_code,
            "OVRS_EXCG_CD": exchange_code,
            "PDNO": symbol,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": _format_price(price),
            "CTAC_TLNO": "",
            "MGCO_APTM_ODNO": "",
            "SLL_TYPE": sell_type,
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": order_type,
        }
        return self._post(
            "/uapi/overseas-stock/v1/trading/order",
            tr_id=tr_id,
            payload=payload,
        )

    def _get(self, path: str, tr_id: str, params: dict) -> dict:
        response = requests.get(
            f"{self.credentials.base_url}{path}",
            headers=self._headers(tr_id=tr_id),
            params=params,
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def _post(self, path: str, tr_id: str, payload: dict) -> dict:
        response = requests.post(
            f"{self.credentials.base_url}{path}",
            headers=self._headers(tr_id=tr_id),
            json=payload,
            timeout=self.timeout,
        )
        return self._handle_response(response)

    def _headers(self, tr_id: str) -> dict:
        token = self._access_token()
        return {
            "content-type": "application/json",
            "accept": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.credentials.app_key,
            "appsecret": self.credentials.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
            "user-agent": self.credentials.user_agent,
        }

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token

        response = requests.post(
            f"{self.credentials.base_url}/oauth2/tokenP",
            headers={
                "content-type": "application/json",
                "user-agent": self.credentials.user_agent,
            },
            json={
                "grant_type": "client_credentials",
                "appkey": self.credentials.app_key,
                "appsecret": self.credentials.app_secret,
            },
            timeout=self.timeout,
        )
        data = self._handle_response(response)
        token = data.get("access_token")
        if not token:
            raise RuntimeError("KIS token response did not include access_token")
        self._token = token
        self._token_expiry = time.time() + (60 * 50)
        return token

    def _handle_response(self, response: requests.Response) -> dict:
        response.raise_for_status()
        data = response.json()
        if str(data.get("rt_cd", "0")) != "0":
            raise RuntimeError(f"KIS API error {data.get('msg_cd')}: {data.get('msg1')}")
        return data

    def _pick_domestic_tr_id(self, side: str) -> str:
        if self.credentials.env == "demo":
            return "VTTC0012U" if side == "buy" else "VTTC0011U"
        return "TTTC0012U" if side == "buy" else "TTTC0011U"

    def _pick_overseas_tr_id(self, side: str, exchange_code: str) -> str:
        us_buy = "TTTT1002U"
        us_sell = "TTTT1006U"
        base = us_buy if side == "buy" else us_sell
        if exchange_code not in {"NASD", "NYSE", "AMEX"}:
            raise ValueError(f"Unsupported overseas exchange for this adapter: {exchange_code}")
        if self.credentials.env == "demo":
            return "V" + base[1:]
        return base

    @staticmethod
    def _load_credentials(env: str) -> KisCredentials:
        normalized = "demo" if env == "demo" else "real"
        prefix = "KIS_PAPER_" if normalized == "demo" else "KIS_"
        base_url = (
            os.getenv(f"{prefix}BASE_URL")
            or ("https://openapivts.koreainvestment.com:29443" if normalized == "demo" else "https://openapi.koreainvestment.com:9443")
        )
        app_key = os.getenv(f"{prefix}APP_KEY", "")
        app_secret = os.getenv(f"{prefix}APP_SECRET", "")
        account_no = os.getenv(f"{prefix}ACCOUNT_NO", "")
        product_code = os.getenv(f"{prefix}ACCOUNT_PRODUCT_CODE") or os.getenv("KIS_ACCOUNT_PRODUCT_CODE", "01")
        user_agent = os.getenv("KIS_USER_AGENT", "Mozilla/5.0")
        if not app_key or not app_secret or not account_no:
            raise RuntimeError(
                f"Missing KIS credentials for env={normalized}. Required: {prefix}APP_KEY, {prefix}APP_SECRET, {prefix}ACCOUNT_NO"
            )
        return KisCredentials(
            app_key=app_key,
            app_secret=app_secret,
            account_no=account_no,
            product_code=product_code,
            base_url=base_url,
            user_agent=user_agent,
            env=normalized,
        )


def infer_overseas_exchange(symbol: str) -> str:
    if symbol.isalpha() and len(symbol) <= 5:
        return "NASD"
    return "NASD"


def _to_float(value: object) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _format_price(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"
