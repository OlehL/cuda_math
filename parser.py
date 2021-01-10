import re
from decimal import Decimal as D


class TreeItem:
    """
    :param s: line
    :param i: line number
    """
    tabsize = 1
    __slots__ = ['parent', 's', 'i', 'offset', 'subitems', 'local']

    def __init__(self, parent, s: str, i: int, offset: int):
        self.parent = parent
        self.s = s
        self.i = i
        self.offset = offset
        self.subitems = []
        self.local = {}

    def add(self, s: str, i: int, offset: int):
        """Add sub item.
        :param s: line
        :param i: line number
        """
        ti = TreeItem(self, s, i, offset)
        self.subitems.append(ti)
        return ti

    def hassubitems(self):
        return True if self.subitems else False

    def __repr__(self):
        return str({'line': self.i, 'val': self.s, 'offset': self.offset})


class Tree:
    tabsize = 1

    def __init__(self):
        self.offset = -1
        self.parent = None
        self.subitems = []

    def add(self, s: str, i: int, offset: int):
        """Add sub item.
        :param s: line
        :param i: line number
        """
        ti = TreeItem(self, s, i, offset)
        self.subitems.append(ti)
        return ti

    def hassubitems(self):
        return True if self.subitems else False

    @staticmethod
    def set_tab_size(val: int):
        Tree.tabsize = val
        TreeItem.tabsize = val


def get_offet(ln):
    offset = 0
    for s in ln:
        if s == ' ':
            offset += 1
        elif s == '\t':
            offset += Tree.tabsize
        else:
            return offset
    return offset


class Expression:
    __slots__ = ['s', 'start', 'end']

    def __init__(self, s, start, end):
        self.s = s
        self.start = start
        self.end = end


class Parser:
    def __init__(self):
        self.re_header = re.compile(r'^\s*(\w+.*?):\s*$')
        self.re_expression = re.compile(r"\S+?={1,2}\S*")
        self.re_comment = re.compile(r'\s*?#.*$')
        self._operands = '()=<!>+-*/^²³'

    @staticmethod
    def getbool(val):
        return True if val else False

    def hasexpresion(self, line):
        line = line.split('#')[0]
        return self.getbool(self.re_expression.match(line))

    def isexpresion(self, s):
        for i in s:
            if i in self._operands:
                return True
        return False

    @staticmethod
    def isvar(s):
        if not s:
            return False
        m = '+-*/^²³\\:;[](){}<>=!,.?&%#@'
        for i in s:
            if i in m:
                return False
        return True

    @staticmethod
    def isdecimal(s):
        if not s:
            return False
        try:
            D(s)
            return True
        except Exception as ex:
            return False

    @staticmethod
    def isbool(s):
        if isinstance(s, str):
            if s.lower() == 'true' or s.lower() == 'false':
                return True
        elif isinstance(s, bool):
            return True
        else:
            return False

    def get_expression(self, s):
        """find expressions in s"""
        s = s.split('#')[0]
        expressions = []
        for m in self.re_expression.finditer(s):
            expressions.append(Expression(m.group(0), m.start(), m.end()))
        return expressions

    @staticmethod
    def split_expression(exp: str):
        """
        exp γ1=(1.82*0.7+(1.94-1)/(1+0.8)*1.4+1.86*1.9)=1.3
        return ['γ1', '(1.82*0.7+(1.94-1)/(1+0.8)*1.4+1.86*1.9)', '1.3']
        """
        pat = '=<!>'
        part = []
        start = 0
        true_eq = 0
        for _ in range(exp.count('=')):
            eq = exp.find('=', start)
            if exp[eq-1] not in pat:
                if (eq + 1 < len(exp) and exp[eq+1] not in '=') or eq + 1 == len(exp):
                    part.append(exp[true_eq:eq])
                    true_eq = eq + 1
            start = eq + 1
        part.append(exp[true_eq:])
        return part

    def get_val(self, v):
        if not isinstance(v, str):
            return v
        if self.isdecimal(v):
            return D(v)
        elif v.lower() == 'true':
            return True
        elif v.lower() == 'false':
            return False
        else:
            return v.replace(', ', ',')


parser = Parser()


def find_parens(s):
    """Find pairs of ()"""
    res = {}
    stack = []

    for i, c in enumerate(s):
        if c == '(':
            stack.append(i)
        elif c == ')':
            if len(stack) == 0:
                raise IndexError("No matching closing parens at: " + str(i))
            res[stack.pop()] = i

    if len(stack) > 0:
        raise IndexError("No matching opening parens at: " + str(stack.pop()))

    return res
