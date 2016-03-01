import time
import datetime

numbers = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
levels = ['', '十', '百', '千', '万']


def translate(n, level=0, zero_tail=True):
    if not n:
        return ''
    curr_digit = n % 10
    prev_digit = n // 10
    zero_tail = zero_tail and curr_digit == 0
    zero_continue = not zero_tail and curr_digit == 0 and prev_digit % 10 == 0
    return (translate(prev_digit, level=level + 1, zero_tail=zero_tail) +
            ((((numbers[curr_digit] + (levels[level]
                                        if curr_digit else ''))
               if not zero_continue else '')
              if not zero_tail else '')))


def once_only(rate, nper, pv):
    for i in range(1, nper):
        yield (0, 0)
    yield (pv, rate * nper * pv)


def interest_first(rate, nper, pv):
    for i in range(1, nper):
        yield (0, 0)
    yield (pv, 0)


def capital_final(rate, nper, pv):
    IN = pv * rate
    for i in range(1, nper):
        yield (0, IN)
    yield (pv, IN)


def average_capital(rate, nper, pv):
    rv = pv / nper
    for i in range(1, nper+1):
        IN = pv * rate
        pv -= rv
        yield (rv, IN)


def average_capital_plus_interest(rate, nper, pv):
    rv = pv * rate * (1+rate)**nper / ((1 + rate)**nper - 1)
    for i in range(1, nper+1):
        IN = pv * rate
        pr = rv - IN
        pv -= pr
        yield (pr, IN)


def relative_timestamp(base, relative_delta):
    return time.mktime((base + datetime.timedelta(1) + relative_delta).timetuple())
