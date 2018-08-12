# -*- coding: utf-8 -*-

import argparse
import json
import os

try:
    import urwid
except ImportError:
    import sys

    root_dir = os.path.dirname(os.path.abspath(__file__))
    urwid_dir = os.path.join(root_dir, 'urwid')
    sys.path.append(urwid_dir)
    import urwid

# 'class name', 'color', 'background-color'
palette = [
    ('title', urwid.BLACK, urwid.WHITE),
    ('background', urwid.WHITE, urwid.BLACK),

    ('focus', urwid.YELLOW, urwid.BLACK, 'standout'),

    ('text.important', urwid.WHITE, urwid.BLACK, 'standout'),

    ('server_list.parent_node', urwid.LIGHT_GRAY, urwid.BLACK),
    ('server_list.node', urwid.WHITE, urwid.BLACK),
    ('server_list.node focus', urwid.LIGHT_BLUE, urwid.BLACK)
]

main_loop = urwid.MainLoop(None, palette, handle_mouse=False)


class GWKitApplication:
    def __init__(self, server_config, test_mode, username='irteam', keyword='', *args, **kwargs):
        self._username = username
        self._keyword = keyword
        self._server_config = json.load(file(server_config))
        self._test_mode = test_mode

    def initialize(self):
        self._kinit()

    def get_server_list(self, keyword=None):
        return self._server_config

    @property
    def username(self):
        return self._username

    @property
    def keyword(self):
        return self._keyword

    def rlogin(self, hostname):
        command = 'rlogin -l {0} {1}'.format(self.username, hostname)
        os.system(command)
        main_loop.screen.clear()

    def append_keyword(self, key):
        self._keyword = self._keyword + key

    def clear_keyword(self):
        self._keyword = ''

    def delete_keyword(self):
        self._keyword = self._keyword[0:-1]

    def rotate_username(self):
        self._username = 'irteam' if self._username == 'irteamsu' else 'irteamsu'

    def _kinit(self):
        os.system('kinit')


class StatusBar(urwid.WidgetWrap):
    def __init__(self, username='', keyword=''):
        self.username_edit = urwid.Edit('Username : ', edit_text=username)
        self.keyword_edit = urwid.Edit('Keyword : ', edit_text=keyword)
        column_widgets = [self.username_edit, self.keyword_edit]
        status_columns = urwid.Columns(column_widgets)
        container = urwid.LineBox(status_columns, 'Status', title_align=urwid.LEFT)

        urwid.WidgetWrap.__init__(self, container)

    def connect_signals(self, gwkit):
        urwid.connect_signal(gwkit, 'username_change', self._update_username)
        urwid.connect_signal(gwkit, 'keyword_change', self._update_keyword)

    def _update_username(self, widget, username):
        self.username_edit.set_edit_text(username)

    def _update_keyword(self, widget, keyword):
        self.keyword_edit.set_edit_text(keyword)


class ServerWidget(urwid.TreeWidget):
    def get_display_text(self):
        return self.get_node().name

    def selectable(self):
        return True

    def keypress(self, size, key):
        if self.is_leaf:
            if key == 'enter':
                gw_app.rlogin(self.get_node().name)
            else:
                return key

        if key in ('+', 'right') and not self.expanded:
            self.expanded = True
            self.update_expanded_icon()
        elif key in ('-', 'left') and self.expanded:
            self.expanded = False
            self.update_expanded_icon()
        elif self._w.selectable():
            return self.__super.keypress(size, key)
        else:
            return key


class ServerDataPropertiesMixin:
    @property
    def name(self):
        return self.get_value()['name']

    @property
    def children(self):
        return self.get_value().get('children', [])

    @property
    def children_size(self):
        return len(self.children)


class ServerNode(urwid.TreeNode, ServerDataPropertiesMixin):
    def load_widget(self):
        return urwid.AttrWrap(ServerWidget(self), 'server_list.node', 'server_list.node focus')


class ServerParentNode(urwid.ParentNode, ServerDataPropertiesMixin):
    def __init__(self, data, container=None, *args, **kwargs):
        super(ServerParentNode, self).__init__(data, *args, **kwargs)
        self.container = container

    def load_widget(self):
        return urwid.AttrWrap(ServerWidget(self), 'server_list.parent_node')

    def load_child_keys(self):
        return range(self.children_size)

    def load_child_node(self, key):
        child_data = self.children[key]
        child_depth = self.get_depth() + 1
        if 'children' in child_data:
            child_class = ServerParentNode
        else:
            child_class = ServerNode
        return child_class(child_data, parent=self, key=key, depth=child_depth)


class ServerTreeListBox(urwid.WidgetWrap):
    def __init__(self):
        self.server_list = {'name': 'no name'}
        self.root_node = ServerNode(self.server_list)
        self.server_list_walker = urwid.TreeWalker(self.root_node)
        self.server_list_box = urwid.TreeListBox(self.server_list_walker)
        container = urwid.LineBox(self.server_list_box, "Server List", title_align=urwid.LEFT)

        urwid.WidgetWrap.__init__(self, container)

    def update_list(self, server_list):
        self.server_list = server_list
        self.root_node = ServerParentNode(server_list)
        self.server_list_walker = urwid.TreeWalker(self.root_node)
        self.server_list_box.body = self.server_list_walker


class GWKit(urwid.Frame):
    signals = ['keyword_change', 'username_change']

    def __init__(self, *args, **kwargs):
        title_bar = urwid.AttrMap(urwid.Padding(urwid.Text('GWKit', align=urwid.CENTER)), 'title')
        self.status_bar = StatusBar(gw_app.username, gw_app.keyword)
        self.server_list_box = ServerTreeListBox()
        self.server_list_box.update_list(gw_app.get_server_list())
        self.status_bar.connect_signals(self)

        super(GWKit, self).__init__(self.server_list_box, urwid.Pile([title_bar, self.status_bar]))

    def keypress(self, size, key):
        if key == 'backspace':
            gw_app.delete_keyword()
            self._emit('keyword_change', gw_app.keyword)

        if not len(key) == 1 and not key.startswith('ctrl'):
            return super(GWKit, self).keypress(size, key)

        if key.isalnum():
            gw_app.append_keyword(key)
            self._emit('keyword_change', gw_app.keyword)
        elif key == 'ctrl k':
            gw_app.clear_keyword()
            self._emit('keyword_change', gw_app.keyword)
        elif key == 'ctrl _':
            gw_app.rotate_username()
            self._emit('username_change', gw_app.username)
        return key


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GWKit')
    parser.add_argument('-c', metavar='CONFIG_PATH', type=str, help='path to server list config file',
                        default='tests/server_config_fixture.json', dest='server_config')
    parser.add_argument('-t', type=bool, help='enable test mode', default=False, dest='test_mode')
    parsed_args = vars(parser.parse_args())

    try:
        urwid.set_encoding('UTF-8')
        gw_app = GWKitApplication(**parsed_args)
        gw_app.initialize()
        gw_kit = GWKit(**parsed_args)
        main_loop = urwid.MainLoop(gw_kit, palette, handle_mouse=False)
        main_loop.run()

    except KeyboardInterrupt, err:
        pass
