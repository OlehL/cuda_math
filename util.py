from typing import List

import cudatext as ct
from cuda_math import parser

NAME = 'Math'


def msg(s):
    ct.msg_status('{}: {}'.format(NAME, s))


class Value:

    def __init__(self):
        self.s = None
        self.get_values()

    def get_values(self):
        carets = ct.ed.get_carets()
        if len(carets) > 1:
            msg('multi-carets not supported')
            return
        x0, y0, x1, y1 = carets[0]
        if (y0, x0) > (y1, x1):
            x0, y0, x1, y1 = x1, y1, x0, y0

        s = ct.ed.get_text_sel()
        if not s:
            msg('text no selected')
            return
        self.s = s
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1


def get_tree(text, tab_size):
    if not isinstance(text, list):
        text = text.split('\n')
    t = parser.Tree()
    t.set_tab_size(tab_size)

    last = t
    for i, ln in enumerate(text):
        if len(ln):
            offset = parser.get_offet(ln)

            if offset == last.offset:
                last = last.parent.add(ln, i, offset)
            elif offset > last.offset:
                last = last.add(ln, i, offset)
            elif offset < last.offset:
                while offset < last.offset:

                    if offset > last.parent.offset:
                        last = last.parent.add(ln, i, offset)
                        break

                    last = last.parent

                    if last is None:
                        print('Wrong indent in line {}'.format(i+1))
                        return

                    if offset == last.offset:
                        last = last.parent.add(ln, i, offset)
                        break
    return t


def find_node_by_line_number(items: List[parser.TreeItem], ln_number):
    for i in items:
        if i.i == ln_number:
            return i
        if i.hassubitems:
            res = find_node_by_line_number(i.subitems, ln_number)
            if res:
                return res


def get_cursor():
    """get current cursor position"""
    carets = ct.ed.get_carets()
    if len(carets) != 1:
        return
    x0, y0, x1, y1 = carets[0]
    if not 0 <= y0 < ct.ed.get_line_count():
        return
    line = ct.ed.get_text_line(y0)
    if not 0 <= x0 <= len(line):
        return
    return (y0, x0)


def get_word_under_cursor(row, col, seps='+*/=.,:-!<>()[]{}\'"\t'):
    """get current word under cursor position"""
    line = ct.ed.get_text_line(row)
    if not 0 <= col <= len(line):
        return '', 0
    for sep in seps:
        if sep in line:
            line = line.replace(sep, ' ')
    s = ''.join([' ', line, ' '])
    start = s.rfind(' ', 0, col+1)
    end = s.find(' ', col+1) - 1
    word = line[start:end]
    return word, col-start  # word, position cursor in word
