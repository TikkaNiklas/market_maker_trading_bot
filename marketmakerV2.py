from datamodel import Order, OrderDepth, TradingState
from typing import List, Dict
import jsonpickle

class Trader:
    def run(self, state: TradingState):
        result = {}
        traderData = {}

        if state.traderData:
            traderData = jsonpickle.decode(state.traderData)
        else:
            traderData = {"positions": {}}

        for product, order_depth in state.order_depths.items():
            orders: List[Order] = []
            position = state.position.get(product, 0)
            traderData["positions"][product] = position

            best_bid = max(order_depth.buy_orders.keys(), default=None)
            best_ask = min(order_depth.sell_orders.keys(), default=None)

            if best_bid is not None and best_ask is not None:
                mid_price = (best_bid + best_ask) / 2
                market_spread = best_ask - best_bid
            elif best_bid is not None:
                mid_price = best_bid
                market_spread = 4
            elif best_ask is not None:
                mid_price = best_ask
                market_spread = 4
            else:
                mid_price = 10
                market_spread = 4

            position_limit = 50
            max_volume = 50
            base_spread = max(1.25, market_spread / 2)
            skew_weight = 0

            skew = position / position_limit
            ask_price = int(mid_price + base_spread - skew * skew_weight)
            bid_price = int(mid_price - base_spread - skew * skew_weight)

            max_buy_volume = max(0, position_limit - position)
            max_sell_volume = max(0, position_limit + position)

            buy_volume = min(max_volume, max_buy_volume)
            sell_volume = min(max_volume, max_sell_volume)

            if buy_volume > 0:
                orders.append(Order(product, bid_price, buy_volume))

            if sell_volume > 0:
                orders.append(Order(product, ask_price, -sell_volume))

            result[product] = orders

        new_traderData = jsonpickle.encode(traderData)
        return result, 0, new_traderData