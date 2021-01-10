import os
import re
import json
from typing import Dict, List
import cudatext as ct
from cuda_options_editor import OptEdD


class Config:
    """Config class.

    :param fn: file name witch will be placed in config folder
    :param meta_cfg: default configs
    """
    def __init__(self, fn: str, meta_cfg: Dict):
        self.file = os.path.join(ct.app_path(ct.APP_DIR_SETTINGS), fn)
        self.__meta = meta_cfg
        self.__default_cfg = {i['opt']: i['def'] for i in meta_cfg}
        self.update()

    @property
    def meta_cfg(self):
        return self.__meta

    def update(self):
        if os.path.exists(self.file):
            self.time_stamp = os.path.getmtime(self.file)
            with open(self.file, 'r', encoding='utf8') as f:
                self.__cfg = self._json_load(f.read())
        else:
            self.time_stamp = 0
            self.__cfg = {}

    @staticmethod
    def _json_load(s, *args, **kwargs):
        """Adapt s for json.loads
        Delete comments
        Delete unnecessary ',' from {,***,} and [,***,]
        """
        def rm_cm(match):
            line = match.group(0)
            pos = 0
            in_str = False
            while pos < len(line):
                ch = line[pos]
                if ch == '\\':
                    pos += 2
                elif ch == '"':
                    in_str = not in_str
                    pos += 1
                elif line[pos:pos+2] == '//' and not in_str:
                    return line[:pos]
            return line

        s = re.sub(r'^.*//.*$', rm_cm, s, flags=re.MULTILINE)  # re.MULTILINE for ^$
        s = re.sub(r'{\s*,', r'{', s)
        s = re.sub(r',\s*}', r'}', s)
        s = re.sub(r'\[\s*,', r'[', s)
        s = re.sub(r',\s*\]', r']', s)
        try:
            return json.loads(s, *args, **kwargs)
        except Exception:
            'Error on load json.'
            return

    def _json_dump(self):
        _dump = {}
        for k in self.__cfg:
            if k not in self.__default_cfg:
                raise AttributeError('Wrong key: {}'.format(k))
                break
            elif self.__cfg[k] != self.__default_cfg[k]:
                _dump[k] = self.__cfg[k]
        with open(self.file, 'w', encoding='utf8') as fp:
            json.dump(_dump, fp, indent=4)

    def __getitem__(self, item):
        if os.path.exists(self.file) and os.path.getmtime(self.file) != self.time_stamp:
            self.update()
        return self.__cfg.get(item, self.__default_cfg[item])

    def __setitem__(self, key, value):
        self.__cfg[key] = value
        self._json_dump()

    def configure(self, title='', subset='', hide_lexer_fil=True):
        """
        Show config dialog

        :param title: dialog caption
        :param subset:  section in user.json, if user.json is used
        :param hide_lexer_fil: hide colunm with lexer config
        """
        how = {
            'hide_lex_fil': hide_lexer_fil,
            'stor_json': self.file,
            }
        OptEdD(
            path_keys_info=self.meta_cfg,
            subset=subset,
            how=how
            ).show(title)
        self.update()
