import re
import math
from decimal import Decimal as Dec
import decimal

from cuda_math.parser import parser
from cuda_math import parser as pr


RE_DIGIT = re.compile(r'\b(\d+\.?\d*[eE][-+]?\d+\.?\d*|\d+\.\d+|(?<=[+\-*/=(),\[{\s<>])\d+)\b')


def math_wrap(func):
    def wrap(*args, **kwargs):
        n_args = [float(v) if isinstance(v, Dec) else v for v in args]
        n_kwargs = {k: float(v) if isinstance(v, Dec) else v for k, v in kwargs.items()}
        return Dec(str(func(*n_args, **n_kwargs)))
    return wrap


def op(func):
    def wrap(x):
        return 1/func(x)
    return wrap


def deg_to_rad(func):
    def wrap(x):
        return func(math.radians(x))
    return wrap


def rad_to_deg(func):
    def wrap(x):
        return math.degrees(func(x))
    return wrap


def _if(boolen, iftrue, iffalse):
    """IF(a<b,1+3,-1)"""
    return iftrue if boolen else iffalse


def _and(*args):
    """AND(arg1,arg2,...,argN)"""
    return True if all(args) else False


def _or(*args):
    """OR(arg1,arg2,...,argN)"""
    return True if any(args) else False


def _not(arg):
    """NOT(2>1)=False"""
    return not arg


def _max(*args):
    """max(arg1,arg2,...,argN)"""
    return max(args)


def _min(*args):
    """min(arg1,arg2,...,argN)"""
    return min(args)


def _sum(*args):
    """sum(arg1,arg2,...,argN)"""
    return sum(args)


def mid(*args):
    """mid(arg1,arg2,...,argN)"""
    return sum(args)/len(args)


def rt(val, n):
    return math.pow(val, 1/n)


def round_val(v, round_mask=Dec('1')):
    rnd = Dec(round_mask) if not isinstance(round_mask, Dec) else round_mask
    v = Dec(v) if not isinstance(v, Dec) else v
    res = (v/rnd).to_integral_value(rounding='ROUND_HALF_UP') * rnd
    try:
        normalized = res.normalize()
        sign, digit, exponent = normalized.as_tuple()
        return normalized if exponent <= 0 else normalized.quantize(1)
    except decimal.InvalidOperation:
        s = str(res)
        return s.rstrip('0').rstrip('.') if '.' in s else s


CONSTS = {
    'True': True,
    'False': False,
    'Pi': Dec(math.pi),
    'E': Dec(math.e),
    'IF': _if,
    'AND': _and,
    'OR': _or,
    'NOT': _not,
}


FUNCS = {
    'max': math_wrap(_max),
    'min': math_wrap(_min),
    'sum': math_wrap(_sum),
    'mid': math_wrap(mid),
    'deg': math_wrap(math.degrees),  # deg(x) радіани в градуси
    'rad': math_wrap(math.radians),  # rad(x) градуси в радіани
    'pow': math_wrap(math.pow),  # pow(x,y) піднести x до степені y
    'sqrt': math_wrap(math.sqrt),  # sqrt(x) квадратний корінь
    'rt': math_wrap(rt),  # rt(x,n) корінь x в n степені
    'cos': math_wrap(deg_to_rad(math.cos)),  # cos(x) косинус з градусів
    'cosec': op(math_wrap(deg_to_rad(math.cos))),  # cosec(x) косеканс з градусів
    'acos': math_wrap(rad_to_deg(math.acos)),  # acos(x) арккосинус в градусах
    'sin': math_wrap(deg_to_rad(math.sin)),  # sin(x) синус з градусів
    'sec': op(math_wrap(deg_to_rad(math.sin))),  # sec(x) секанс з градусів
    'asin': math_wrap(rad_to_deg(math.asin)),  # asin(x) арк синус в градусах
    'tan': math_wrap(deg_to_rad(math.tan)),  # tan(x) тангенс з градусів
    'tg': math_wrap(deg_to_rad(math.tan)),  # tg(x) тангенс з градусів
    'ctg': op(math_wrap(deg_to_rad(math.tan))),  # ctg(x) котангенс з градусів
    'atan': math_wrap(rad_to_deg(math.atan)),  # atan(x) арктангенс в градусах
    'exp': math_wrap(math.exp),  # exp(x) e в степені x
    'log': math_wrap(math.log),  # log(x, [base]) логарифм X по основі base. якщо base не вказано, натуральний логарифм.
    'ln': math_wrap(math.log),  # ln(x) натуральний логарифм.
    'log10': math_wrap(math.log10),  # log10(x) логарифм X по основі 10
    'lg': math_wrap(math.log10),  # log10(x) логарифм X по основі 10
    'hypot': math_wrap(math.hypot),  # hypot(x,y) гіпотенуза sqrt(x*x + y*y)
    'abs': math_wrap(abs),
    'roundup': math_wrap(math.ceil),  # roundup(x) округлити в більшу сторону
    'rounddown': math_wrap(math.floor),  # rounddown(x) округлити в меншу сторону
    'round': math_wrap(math.trunc),  # round(x) округлити до цілого
    'rnd': round_val,  # round(x, mask=1) округлити до заданої маски
    }
GLOB = {
    '__D': Dec,
}
GLOB.update(CONSTS)
GLOB.update(FUNCS)


def has_error(s=''):
    s = s.split('=')[-1]
    if 'None' in s or 'error:' in s:
        return True
    return False


class Calc:
    """parse str and calculate result"""
    def __init__(self, config):
        self.cfg = config
        self.item = None
        self.root_context = {}

    @staticmethod
    def do_eval(s, gcont=None, lcont=None):
        gcont = gcont or GLOB
        lcont = lcont or {}
        try:
            result = eval(s, gcont, lcont)
            return result
        except Exception as ex:
            error = ex.__str__()
            error = error.split(' (')[0]
            error = error.replace('=', '_').replace(' ', '_')
            error = 'error:_' + error
            return error

    @staticmethod
    def operand_replace(s):
        rule = (('^', '**'),
                ('²', '**2'),
                ('³', '**3'),
                ('$', 'ֆ'),
                )
        for r in rule:
            s = s.replace(*r)
        return s

    @staticmethod
    def parse_string_as_decimal(s):
        """
        parse str from: "sin(0.25)+45.25+4"
        to: "sin(__D('0.25'))+__D('45.25')+4"
        """
        def dc_wrap(num):
            return "__D('{0}')".format(num.group(0))

        res = ''
        quotes = ['"', "'"]
        q = quotes
        st = 0
        if '"' in s or "'" in s:
            for i, c in enumerate(s):
                if c in q and q == quotes:
                    q = c
                    res += RE_DIGIT.sub(dc_wrap, s[st:i])
                    st = i
                elif c in q:
                    q = quotes
                    res += s[st:i+1]
                    st = i + 1
            res += RE_DIGIT.sub(dc_wrap, s[st:])
            return res
        else:
            return RE_DIGIT.sub(dc_wrap, s)

    def round_val(self, v):
        rnd = Dec(self.cfg['round_mask'])
        res = (v/rnd).to_integral_value(rounding=self.cfg['round_type']) * rnd
        try:
            normalized = res.normalize()
            sign, digit, exponent = normalized.as_tuple()
            return normalized if exponent <= 0 else normalized.quantize(1)
        except decimal.InvalidOperation:
            s = str(res)
            return s.rstrip('0').rstrip('.') if '.' in s else s

    def get_context(self):
        if not self.item:
            print('not self.item')
            return {}
        c = {}
        c.update(self.root_context)
        # go up
        p = self.item.parent
        while p:
            for lc in p.subitems:
                if lc.i > self.item.i:
                    break
                c.update(lc.local)
            p = p.parent

        # go down
        def go_down(item):
            nonlocal c
            for i in item.subitems:
                c.update(i.local)
                if i.hassubitems:
                    go_down(i)
        go_down(self.item)
        return c

    def __call__(self, s):
        localcontext = self.get_context()

        s = self.operand_replace(s)
        s = self.parse_string_as_decimal(s)

        res = self.do_eval(s, lcont=localcontext)
        if self.cfg['round_enable'] and isinstance(res, Dec):
            return self.round_val(res)
        else:
            return res

    def calc_item(self, item: pr.TreeItem):
        if not item:
            return
        self.item = item
        expessions = parser.get_expression(item.s)
        lightning = []
        for i, exp in enumerate(expessions):

            part = parser.split_expression(exp.s)

            # example: a=3
            if len(part) == 2 and parser.isvar(part[0]):
                res = part[1] if parser.isdecimal(part[1]) else self.__call__(part[1])
                # write to root context
                if part[0][0] == '$':
                    part[0] = part[0].replace('$', 'ֆ')
                    self.root_context.update({part[0]: parser.get_val(res)})
                # write to item context
                else:
                    item.local.update({part[0]: parser.get_val(res)})

            # example: 12+34/w=18
            elif len(part) == 2 and parser.isexpresion(part[0]):
                res = self(part[0])
                part[1] = str(res).replace(', ', ',')
                exp.s = '='.join(part)
                expessions[i] = exp

            # example: a=12+13=25
            elif len(part) > 2:
                res = self(part[-2])
                part[-1] = str(res).replace(', ', ',')
                exp.s = '='.join(part)
                expessions[i] = exp
                if parser.isvar(part[0]):
                    # write to root context
                    if part[0][0] == '$':
                        part[0] = part[0].replace('$', 'ֆ')
                        self.root_context.update({part[0]: parser.get_val(res)})
                    # write to item context
                    else:
                        item.local.update({part[0]: parser.get_val(res)})
        newline = ''
        start = 0
        shift = 0
        for exp in expessions:
            newline += item.s[start:exp.start] + exp.s
            iserror = has_error(exp.s)
            len_exp_short = exp.s.rfind('=') if iserror else len(exp.s)
            lightning.append([shift+exp.start, shift+exp.start+len_exp_short, iserror])
            start = exp.end
            shift += len(exp.s) - (exp.end - exp.start)
        newline += item.s[start:]

        return newline, lightning
