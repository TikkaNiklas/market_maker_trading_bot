from datamodel import Order, TradingState
from typing import List, Dict
import jsonpickle

POSITION_LIMITS = {
    "RAINFOREST_RESIN": 50,
    "KELP": 50,
    "SQUID_INK": 50,
    "CROISSANTS": 250,
    "JAM": 350,
    "DJEMBE": 60,
    "PICNIC_BASKET1": 60,
    "PICNIC_BASKET2": 100
}

FALLBACK_SPREAD = 4
DEFAULT_MIDPRICE = 10000

class Trader:
    def run(self, state: TradingState):
        result = {}
        traderData = {}

        if state.traderData:
            traderData = jsonpickle.decode(state.traderData)
        else:
            traderData = {
                "positions": {},
                "price_history": {},
            }

        order_depths = state.order_depths
        positions = state.position

        # Store midprices for component-based baskets
        component_mid_prices = {}

        for product in order_depths:
            position = positions.get(product, 0)
            traderData["positions"][product] = position
            order_depth = order_depths[product]
            best_bid = max(order_depth.buy_orders.keys(), default=None)
            best_ask = min(order_depth.sell_orders.keys(), default=None)

            # Estimate mid price
            if best_bid is not None and best_ask is not None:
                mid_price = (best_bid + best_ask) / 2
            elif best_bid is not None:
                mid_price = best_bid
            elif best_ask is not None:
                mid_price = best_ask
            else:
                mid_price = DEFAULT_MIDPRICE

            component_mid_prices[product] = mid_price

        # --- Basket Arbitrage Logic ---
        def fair_basket1_price(cmp):  # 6 Croissants + 3 Jam + 1 Djembe
            return 6 * cmp["CROISSANTS"] + 3 * cmp["JAM"] + 1 * cmp["DJEMBE"]

        def fair_basket2_price(cmp):  # 4 Croissants + 2 Jam
            return 4 * cmp["CROISSANTS"] + 2 * cmp["JAM"]

        # Ensure we have prices for basket components
        required = {"CROISSANTS", "JAM", "DJEMBE"}
        if required.issubset(component_mid_prices.keys()):
            b1_fair = fair_basket1_price(component_mid_prices)
            b2_fair = fair_basket2_price(component_mid_prices)
            lhs = 2 * b1_fair
            rhs = 3 * b2_fair + 2 * component_mid_prices["DJEMBE"]

            # Simple arbitrage opportunity check
            if lhs > rhs + 10:
                # B1 overpriced → sell B1, buy components
                result.update(self.try_trade("PICNIC_BASKET1", "sell", state))
                result.update(self.try_trade("PICNIC_BASKET2", "buy", state))
                result.update(self.try_trade("DJEMBE", "buy", state))
            elif rhs > lhs + 10:
                # B2 + DJEMBE overpriced → buy B1, sell components
                result.update(self.try_trade("PICNIC_BASKET1", "buy", state))
                result.update(self.try_trade("PICNIC_BASKET2", "sell", state))
                result.update(self.try_trade("DJEMBE", "sell", state))

        # --- Market making for all products ---
        for product in order_depths:
            orders: List[Order] = []
            position = positions.get(product, 0)
            limit = POSITION_LIMITS.get(product, 100)

            order_depth = order_depths[product]
            best_bid = max(order_depth.buy_orders.keys(), default=None)
            best_ask = min(order_depth.sell_orders.keys(), default=None)

            if best_bid is not None and best_ask is not None:
                mid_price = (best_bid + best_ask) / 2
                spread = best_ask - best_bid
            elif best_bid is not None:
                mid_price = best_bid
                spread = FALLBACK_SPREAD
            elif best_ask is not None:
                mid_price = best_ask
                spread = FALLBACK_SPREAD
            else:
                mid_price = DEFAULT_MIDPRICE
                spread = FALLBACK_SPREAD

            ask_price = int(mid_price + spread / 2)
            bid_price = int(mid_price - spread / 2)

            buy_volume = min(20, limit - position)
            sell_volume = min(20, limit + position)

            if buy_volume > 0:
                orders.append(Order(product, bid_price, buy_volume))
            if sell_volume > 0:
                orders.append(Order(product, ask_price, -sell_volume))

            if product not in result:
                result[product] = []
            result[product].extend(orders)

        return result, 0, jsonpickle.encode(traderData)

    def try_trade(self, product: str, side: str, state: TradingState) -> Dict[str, List[Order]]:
        order_depth = state.order_depths.get(product)
        position = state.position.get(product, 0)
        limit = POSITION_LIMITS.get(product, 100)
        orders = []

        if not order_depth:
            return {}

        if side == "buy":
            asks = sorted(order_depth.sell_orders.items())
            for price, volume in asks:
                buy_vol = min(abs(volume), limit - position)
                if buy_vol > 0:
                    orders.append(Order(product, price, buy_vol))
                    break  # One level deep
        elif side == "sell":
            bids = sorted(order_depth.buy_orders.items(), reverse=True)
            for price, volume in bids:
                sell_vol = min(volume, limit + position)
                sell_vol = min(abs(volume), limit + position)
                if sell_vol > 0:
                    orders.append(Order(product, price, -sell_vol))
                    break
        return {product: orders} if orders else {}
