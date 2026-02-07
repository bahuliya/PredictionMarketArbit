import requests

class Arbitrage:

    def getGas():
        url = "https://api.etherscan.io/v2/api"
        gas_apikey = "8H75CIDHCV3C5TW3IFFZGKU5ZKK9QNQRSC"

        params = {
            "apikey": gas_apikey,
            "chainid": "1",
            "module": "gastracker",
            "action": "gasoracle",
        }

        response = requests.get(url, params=params)
        gas_fee = float(response.json()["result"]["FastGasPrice"])
        return gas_fee

    def calc_arbitrage(kalshi_ask, kalshi_vol, poly_ask, poly_vol):
        capital =  1000
        target_roi = 0.25

        gas = .07
        adjusted_capital = capital - gas
        cost_per_contract = kalshi_ask + poly_ask + (0.07 * kalshi_ask * (1 - kalshi_ask))
        contracts = min(adjusted_capital / cost_per_contract , kalshi_vol, poly_vol)
        roi = ((contracts - capital) / (capital)) * 100
        if roi > 0:
            print(roi, "Kalshi Ask:", kalshi_ask, "Poly Ask:", poly_ask)
        return roi >= target_roi, roi