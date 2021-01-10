import cudatext as ct
from typing import List

from cuda_math.calc import Calc, FUNCS, CONSTS
from cuda_math.config import Config
from cuda_math import parser
from cuda_math.util import (
    NAME,
    msg,
    Value,
    get_tree,
    find_node_by_line_number,
    get_cursor,
    get_word_under_cursor
)


TAG = 177
ERROR = "Can't calculate it."
THEME_SYNTAX = ct.app_proc(ct.PROC_THEME_SYNTAX_DICT_GET, '')
TAG_COLOR = THEME_SYNTAX['Symbol']
TAG_COLOR_BAD = THEME_SYNTAX['SymbolBad']
META_INFO = [
    {"opt": "round_enable",
     "cmt": ["show results as round"],
     "def": True,
     "frm": "bool",
     },
    {"opt": "round_mask",
     "cmt": ["Mask for round"],
     "def": "0.0001",
     "frm": "str",
     },
    {"opt": "round_type",
     "cmt": ["type round results"],
     "def": "ROUND_HALF_UP",
     "frm": "strs",
     "lst": ["ROUND_CEILING",
             "ROUND_DOWN",
             "ROUND_FLOOR",
             "ROUND_HALF_DOWN",
             "ROUND_HALF_EVEN",
             "ROUND_HALF_UP",
             "ROUND_UP",
             "ROUND_05UP"
             ]
     },
    ]


class Command:

    def __init__(self):
        cfg = Config(fn='cuda_math.json', meta_cfg=META_INFO)
        self.calc = Calc(cfg)
        self.t = None

    def configure(self):
        self.calc.cfg.configure(title=NAME)

    @property
    def lexer(self):
        return ct.ed.get_prop(ct.PROP_LEXER_FILE)

    def on_change_slow(self, _):
        if self.lexer != 'Math':
            return
        # off event. Otherwise the calc_all runs two times.
        ev = 'on_change_slow,on_complete'
        ct.app_proc(ct.PROC_SET_EVENTS, 'cuda_math'+';on_complete;;')

        self.calc_all()

        # on event
        ct.timer_proc(
            ct.TIMER_START_ONE,
            lambda tag='', info='': ct.app_proc(ct.PROC_SET_EVENTS, 'cuda_math'+';'+ev+';;'),
            interval=1000
        )

    def calc_sel_and_replace(self):
        val = Value()
        if not val.s:
            msg(ERROR)
            return
        res = self.calc(val.s)
        if res:
            ct.ed.set_caret(val.x0, val.y0)
            ct.ed.delete(val.x0, val.y0, val.x1, val.y1)
            ct.ed.insert(val.x0, val.y0, res)
            ct.msg_status('CalcExpr: replaced to: {}'.format(res))

    def calc_sel_and_append(self):
        val = Value()
        if not val.s:
            msg(ERROR)
            return
        res = self.calc(val.s)
        if res:
            msg('result: {}'.format(res))
            ct.ed.insert(val.x1, val.y1, "="+res)
            ct.ed.set_caret(val.x1+len(res)+1, val.y1)

    def calc_sel_and_show(self):
        val = Value()
        if not val.s:
            msg(ERROR)
            return
        res = self.calc(val.s)
        if res:
            msg('result: {}'.format(res))
            ct.app_proc(ct.PROC_SET_CLIP, res)

    def calc_all(self):
        if self.lexer not in ['Math', '']:
            ct.msg_status("This command works only for plain text or lexer 'Math'.")
            return
        ct.ed.attr(ct.MARKERS_DELETE_BY_TAG, TAG)

        self.t = get_tree(text=ct.ed.get_text_all(),
                          tab_size=ct.ed.get_prop(ct.PROP_TAB_SIZE))

        self.calc.root_context = {}
        self.calc_items(self.t.subitems)

    def calc_items(self, items: List[parser.TreeItem]):
        for item in items:
            if item.hassubitems:
                self.calc_items(item.subitems)

            res = self.calc.calc_item(item)
            if item.s != res[0]:
                ct.ed.set_text_line(item.i, res[0])
            for h in res[1]:
                if h[2]:
                    ct.ed.attr(ct.MARKERS_ADD, TAG,
                               h[0],
                               item.i,
                               h[1]-h[0],
                               color_font=TAG_COLOR_BAD['color_font'],
                               color_border=TAG_COLOR_BAD['color_border'],
                               border_down=1,
                               show_on_map=True)

    def on_complete(self, _):
        if self.lexer not in ['Math']:
            return

        if not self.t:
            return

        context = []
        context.extend([{'type': 'func', 'val': k} for k in FUNCS.keys()])
        context.extend([{'type': ' ', 'val': k} for k in CONSTS.keys()])

        _, y1, _, y2 = ct.ed.get_carets()[0]
        y = max(y1, y2)
        item = find_node_by_line_number(self.t.subitems, y)

        self.calc.calc_item(item)
        local_context = self.calc.get_context()
        context.extend([{'type': 'var', 'val': k.replace('ֆ', '$')} for k in local_context.keys()])

        cursor = get_cursor()
        if not cursor:
            return
        word, pos = get_word_under_cursor(*cursor)
        if not word:
            return
        source = word[:pos]
        complete_list = ['|'.join([i['type'], i['val']]) for i in context if i['val'].find(source) == 0]

        if not complete_list:
            return True

        ct.ed.complete('\n'.join(complete_list), pos, len(word)-pos)
        return True
