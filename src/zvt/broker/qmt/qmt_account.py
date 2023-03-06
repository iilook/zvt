# -*- coding: utf-8 -*-
import logging
from typing import List

from xtquant import xtconstant
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount

from zvt.broker.qmt.qmt_api import _to_qmt_code
from zvt.trader import AccountService, TradingSignal, OrderType, TradingSignalType, trading_signal_type_to_order_type

logger = logging.getLogger(__name__)


def _to_qmt_order_type(order_type: OrderType):
    if order_type == OrderType.order_long:
        return xtconstant.STOCK_BUY
    elif order_type == OrderType.order_close_long:
        return xtconstant.STOCK_SELL


class MyXtQuantTraderCallback(XtQuantTraderCallback):
    def on_connected(self):
        super().on_connected()

    def on_smt_appointment_async_response(self, response):
        super().on_smt_appointment_async_response(response)

    def on_cancel_order_stock_async_response(self, response):
        super().on_cancel_order_stock_async_response(response)

    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        print("connection lost")

    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        :return:
        """
        print("on order callback:")
        print(order.stock_code, order.order_status, order.order_sysid)

    def on_stock_asset(self, asset):
        """
        资金变动推送
        :param asset: XtAsset对象
        :return:
        """
        print("on asset callback")
        print(asset.account_id, asset.cash, asset.total_asset)

    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        print("on trade callback")
        print(trade.account_id, trade.stock_code, trade.order_id)

    def on_stock_position(self, position):
        """
        持仓变动推送
        :param position: XtPosition对象
        :return:
        """
        print("on position callback")
        print(position.stock_code, position.volume)

    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        print("on order_error callback")
        print(order_error.order_id, order_error.error_id, order_error.error_msg)

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        print("on cancel_error callback")
        print(cancel_error.order_id, cancel_error.error_id, cancel_error.error_msg)

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        print("on_order_stock_async_response")
        print(response.account_id, response.order_id, response.seq)

    def on_account_status(self, status):
        """
        :param response: XtAccountStatus 对象
        :return:
        """
        print("on_account_status")
        print(status.account_id, status.account_type, status.status)


class QmtStockAccount(AccountService):
    def __init__(self, path, account_id) -> None:
        session_id = 123456
        self.xt_trader = XtQuantTrader(path, session_id)

        # StockAccount可以用第二个参数指定账号类型，如沪港通传'HUGANGTONG'，深港通传'SHENGANGTONG'
        self.account = StockAccount(account_id=account_id, account_type="STOCK")

        # 创建交易回调类对象，并声明接收回调
        callback = MyXtQuantTraderCallback()
        self.xt_trader.register_callback(callback)

        # 启动交易线程
        self.xt_trader.start()

        # 建立交易连接，返回0表示连接成功
        connect_result = self.xt_trader.connect()
        if connect_result != 0:
            import sys

            sys.exit("链接失败，程序即将退出 %d" % connect_result)

        # 对交易回调进行订阅，订阅后可以收到交易主推，返回0表示订阅成功
        subscribe_result = self.xt_trader.subscribe(self.account)
        if subscribe_result != 0:
            logger.error(f"账号订阅失败 {subscribe_result}")

    def get_current_position(self, entity_id):
        print("query positions:")
        positions = self.xt_trader.query_stock_positions(self.account)
        print("positions:", len(positions))
        if len(positions) != 0:
            print("last position:")
            print("{0} {1} {2}".format(positions[-1].account_id, positions[-1].stock_code, positions[-1].volume))

        # 根据股票代码查询对应持仓
        stock_code = _to_qmt_code(entity_id=entity_id)
        print("query position:")
        position = self.xt_trader.query_stock_position(self.account, stock_code)
        if position:
            print("position:")
            print("{0} {1} {2}".format(position.account_id, position.stock_code, position.volume))

    def get_current_account(self):
        # 查询证券资产
        print("query asset:")
        asset = self.xt_trader.query_stock_asset(self.account)
        if asset:
            print("asset:")
            print("cash {0}".format(asset.cash))

    def order(
        self,
        entity_id,
        current_price,
        signal_timestamp,
        order_amount=0,
        order_pct=1.0,
        order_price=0,
        order_type=OrderType.order_long,
        order_money=0,
    ):
        stock_code = _to_qmt_code(entity_id=entity_id)
        fix_result_order_id = self.xt_trader.order_stock(
            account=self.account,
            stock_code=stock_code,
            order_type=_to_qmt_order_type(order_type=order_type),
            order_volume=order_amount,
            price_type=xtconstant.FIX_PRICE,
            price=order_price,
            strategy_name="strategy_name",
            order_remark="remark",
        )

    def on_trading_signals(self, trading_signals: List[TradingSignal]):
        for trading_signal in trading_signals:
            try:
                self.handle_trading_signal(trading_signal)
            except Exception as e:
                logger.exception(e)
                self.on_trading_error(timestamp=trading_signal.happen_timestamp, error=e)

    def handle_trading_signal(self, trading_signal: TradingSignal):
        entity_id = trading_signal.entity_id
        happen_timestamp = trading_signal.happen_timestamp
        order_type = trading_signal_type_to_order_type(trading_signal.trading_signal_type)
        trading_level = trading_signal.trading_level.value

        self.order(
            entity_id=entity_id,
            current_price=0,
            signal_timestamp=happen_timestamp,
            order_pct=trading_signal.position_pct,
            order_type=order_type,
            order_money=trading_signal.order_money,
        )

    def on_trading_open(self, timestamp):
        pass

    def on_trading_close(self, timestamp):
        pass

    def on_trading_finish(self, timestamp):
        pass

    def on_trading_error(self, timestamp, error):
        pass
