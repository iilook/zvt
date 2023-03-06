# -*- coding: utf-8 -*-

from xtquant import xtdata

from zvt.contract import IntervalLevel, AdjustType
from zvt.contract.api import decode_entity_id


# http://docs.thinktrader.net/vip/QMT-Simple/


def _to_qmt_code(entity_id):
    _, exchange, code = decode_entity_id(entity_id=entity_id)
    return f"{code}.{exchange.upper()}"


def _to_qmt_dividend_type(adjust_type: AdjustType):
    if adjust_type == AdjustType.qfq:
        return "front"
    elif adjust_type == AdjustType.hfq:
        return "back"
    else:
        return "none"


def get_kdata(
    entity_id,
    start_timestamp,
    end_timestamp,
    level=IntervalLevel.LEVEL_1DAY,
    adjust_type=AdjustType.qfq,
):
    code = _to_qmt_code(entity_id=entity_id)
    data = xtdata.get_local_data(
        stock_code=code,
        period=level,
        start_time=start_timestamp,
        end_time=end_timestamp,
        dividend_type=_to_qmt_dividend_type(adjust_type=adjust_type),
        fill_data=True,
    )
    return data


if __name__ == "__main__":
    print(get_kdata(entity_id="stock_sz_000338"))
