# -*- coding: utf-8 -*-

"""
This file is part of QualCoder.

QualCoder is free software: you can redistribute it and/or modify it under the
terms of the GNU Lesser General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later version.

QualCoder is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with QualCoder.
If not, see <https://www.gnu.org/licenses/>.

Author: Colin Curtain C, Kai Dröge, Justin Missaghieh--Poncet, Lorenzo Salomón
https://github.com/ccbogel/QualCoder
https://qualcoder.wordpress.com/
https://qualcoder-org.github.io
https://qualcoder.org/
"""

import datetime
import logging

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import Qt
import qtawesome as qta

from .add_item_name import DialogAddItemName
from .confirm_delete import DialogConfirmDelete
from .file_folders import FileTreeBase, FOLDER_PREFIX, KEY_COL, NAME_COL
from .memo import DialogMemo
from .select_items import DialogSelectItems

logger = logging.getLogger(__name__)

ALL_CASES_KEY = "allcases"
NO_CASE_KEY = "nocase"
CASE_PREFIX = "caseid:"
NO_CASE = -1  # current_caseid value for files without a case


class FileCaseTreeController(FileTreeBase):
    """ Flat case list for the Manage files dialog, each case shows its files.
    Selecting a case filters the file table. Dropping files (or folders from the
    folder tree) onto a case assigns the whole files to it; existing links are kept.
    Signals:
        case_selected(object) - case id, NO_CASE, or None for all files
        cases_changed(list) - changed database table names
    """

    case_selected = QtCore.pyqtSignal(object)
    cases_changed = QtCore.pyqtSignal(list)

    def __init__(self, app, tree_widget: QtWidgets.QTreeWidget, host):
        super().__init__(app, tree_widget, host, _("Cases"))
        self.cases = []  # Dictionaries: caseid, name, memo
        self.case_files = {}  # caseid -> set of file ids
        self.current_caseid = None
        self.expanded = set()  # Case nodes opened by the user; cases start collapsed
        self._icon_case = None
        self._icon_all = None
        self._icon_none = None
        self.tree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragDrop)
        self.tree.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.tree.currentItemChanged.connect(self._on_current_item_changed)
        self.tree.itemExpanded.connect(lambda item: self.expanded.add(item.text(KEY_COL)))
        self.tree.itemCollapsed.connect(lambda item: self.expanded.discard(item.text(KEY_COL)))

    # Data

    def load_cases(self):
        cur = self.app.conn.cursor()
        cur.execute("select caseid, name, ifnull(memo,'') from cases order by lower(name)")
        self.cases = [{'caseid': r[0], 'name': r[1], 'memo': r[2]} for r in cur.fetchall()]
        self.case_files = {c['caseid']: set() for c in self.cases}
        cur.execute("select distinct caseid, fid from case_text")
        for caseid, fid in cur.fetchall():
            if caseid in self.case_files:
                self.case_files[caseid].add(fid)

    def case_by_id(self, caseid):
        for c in self.cases:
            if c['caseid'] == caseid:
                return c
        return None

    def files_with_a_case(self) -> set:
        ids = set()
        for fids in self.case_files.values():
            ids |= fids
        return ids

    def filter_file_ids(self):
        """ Ids of the files in the selected case, None when all files. """

        if self.current_caseid is None:
            return None
        if self.current_caseid == NO_CASE:
            with_case = self.files_with_a_case()
            return {s['id'] for s in self.host.source if s['id'] not in with_case}
        return set(self.case_files.get(self.current_caseid, set()))

    def current_label(self) -> str:
        if self.current_caseid is None:
            return ""
        if self.current_caseid == NO_CASE:
            return _("No case")
        case_ = self.case_by_id(self.current_caseid)
        return case_['name'] if case_ is not None else ""

    # Keys

    @staticmethod
    def key_caseid(key):
        """ Case id from a tree key: an int, NO_CASE, or None for the root. """

        if key.startswith(CASE_PREFIX):
            return int(key[len(CASE_PREFIX):])
        if key == NO_CASE_KEY:
            return NO_CASE
        return None

    @staticmethod
    def caseid_key(caseid) -> str:
        if caseid is None:
            return ALL_CASES_KEY
        if caseid == NO_CASE:
            return NO_CASE_KEY
        return f"{CASE_PREFIX}{caseid}"

    def item_caseid(self, item):
        """ Case of a node, or of the case a file node sits under. """

        if item is None:
            return None
        key = self.item_key(item)
        if self.key_fid(key) is not None:
            return self.key_caseid(self.item_key(item.parent()))
        return self.key_caseid(key)

    # Tree fill

    def fill_tree(self):
        """ Fill the tree: All files root, one node per case with its files,
        then a No case node. Selection and opened cases survive a refill. """

        self.load_cases()
        if self._icon_case is None:
            self._icon_case = qta.icon('mdi6.briefcase-outline')
            self._icon_all = qta.icon('mdi6.briefcase-variant-outline')
            self._icon_none = qta.icon('mdi6.briefcase-off-outline')
        blocker = QtCore.QSignalBlocker(self.tree)
        self.tree.clear()
        root = QtWidgets.QTreeWidgetItem([_("All files"), "", ALL_CASES_KEY])
        root.setIcon(NAME_COL, self._icon_all)
        root.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        self.tree.addTopLevelItem(root)
        sources = {s['id']: s for s in self.host.source}
        node_index = {None: root}
        for case_ in self.cases:
            node = QtWidgets.QTreeWidgetItem([case_['name'], "", self.caseid_key(case_['caseid'])])
            node.setIcon(NAME_COL, self._icon_case)
            fids = self.case_files.get(case_['caseid'], set())
            node.setToolTip(NAME_COL, f"{case_['name']}\n{len(fids)} " + _("Files"))
            self.set_memo_cell(node, case_['memo'])
            node.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled |
                          Qt.ItemFlag.ItemIsDropEnabled)
            root.addChild(node)
            node_index[case_['caseid']] = node
            for fid in sorted(fids, key=lambda f: sources[f]['name'].lower() if f in sources else ""):
                if fid in sources:
                    node.addChild(self.make_file_item(sources[fid]))
        no_case = QtWidgets.QTreeWidgetItem([_("No case"), "", NO_CASE_KEY])
        no_case.setIcon(NAME_COL, self._icon_none)
        no_case.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
        with_case = self.files_with_a_case()
        for s in self.host.source:
            if s['id'] not in with_case:
                no_case.addChild(self.make_file_item(s))
        root.addChild(no_case)
        node_index[NO_CASE] = no_case
        root.setExpanded(True)
        present = set()
        for i in range(root.childCount()):
            node = root.child(i)
            if node.childCount() > 0:
                present.add(node.text(KEY_COL))
            node.setExpanded(node.text(KEY_COL) in self.expanded)
        self.expanded &= present
        self.finish_fill()
        target = node_index.get(self.current_caseid)
        if target is None:
            self.current_caseid = None
            target = root
        self.tree.setCurrentItem(target)
        if self.current_caseid is None:
            self.tree.clearSelection()
        blocker.unblock()
        self.apply_search()

    def set_current_case(self, caseid):
        """ Change the case filter from outside the tree. """

        if caseid is None:
            self.clear_filter()
            return
        self.current_caseid = caseid
        self.highlight_key(self.caseid_key(caseid))

    def clear_filter(self):
        self.current_caseid = None
        self.show_root_unselected()

    def has_filter(self) -> bool:
        return self.current_caseid is not None

    # Selection

    def _on_current_item_changed(self, current, previous):
        key = self.item_key(current)
        if key == "" or self.key_fid(key) is not None:
            return
        caseid = self.key_caseid(key)
        if caseid != self.current_caseid:
            self.current_caseid = caseid
            self.case_selected.emit(caseid)

    def file_clicked(self, item, fid):
        self.host.tree_file_selected(fid, caseid=self.item_caseid(item), from_cases=True)

    def edit_memo(self, item) -> bool:
        caseid = self.key_caseid(self.item_key(item))
        if caseid is None or caseid == NO_CASE:
            return False
        self.case_memo(caseid)
        return True

    # Drag and drop

    def items_dropped(self, items, target, internal: bool):
        """ Files or folders dropped onto a case are assigned to it. """

        caseid = self.item_caseid(target)
        if caseid is None or caseid == NO_CASE:
            return
        fids = []
        for item in items:
            key = self.item_key(item)
            fid = self.key_fid(key)
            if fid is not None:
                fids.append(fid)
            elif key.startswith(FOLDER_PREFIX):
                # A folder from the folder tree brings its whole branch
                folderid = int(key[len(FOLDER_PREFIX):])
                fids.extend(self.host.folder_tree.branch_file_ids(folderid))
        self.assign_files_to_case(list(dict.fromkeys(fids)), caseid)

    def assign_files_to_case(self, fids, caseid) -> list:
        """ Link the whole files to a case. Returns the ids that were newly linked. """

        if not fids or self.case_by_id(caseid) is None:
            return []
        cur = self.app.conn.cursor()
        now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        added = []
        for fid in fids:
            cur.execute("select fulltext from source where id=?", [fid])
            res = cur.fetchone()
            len_text = len(res[0]) if res is not None and res[0] is not None else 0
            cur.execute("select count(*) from case_text where caseid=? and fid=? and pos0=? and pos1=?",
                        [caseid, fid, 0, len_text])
            if cur.fetchone()[0] > 0:
                continue
            cur.execute("insert into case_text (caseid, fid, pos0, pos1, owner, date, memo) values(?,?,?,?,?,?,?)",
                        [caseid, fid, 0, len_text, self.app.settings['codername'], now, ""])
            added.append(fid)
        if not added:
            return []
        self.app.conn.commit()
        self.app.delete_backup = False
        self.after_change(added, ["case_text"])
        return added

    def remove_files_from_case(self, fids, caseid):
        """ Unlink files from a case. Asks first when partial text segments would be lost. """

        if not fids or caseid is None or caseid == NO_CASE:
            return
        cur = self.app.conn.cursor()
        partial = []
        for fid in fids:
            cur.execute("select fulltext from source where id=?", [fid])
            res = cur.fetchone()
            len_text = len(res[0]) if res is not None and res[0] is not None else 0
            cur.execute("select count(*) from case_text where caseid=? and fid=? and not (pos0=0 and pos1=?)",
                        [caseid, fid, len_text])
            if cur.fetchone()[0] > 0:
                source = self.source_by_id(fid)
                partial.append(source['name'] if source is not None else str(fid))
        if partial:
            msg = _("These files have text segments linked to the case. All links will be removed:")
            ui = DialogConfirmDelete(self.app, msg + "\n" + "\n".join(partial))
            if not ui.exec():
                return
        for fid in fids:
            cur.execute("delete from case_text where caseid=? and fid=?", [caseid, fid])
        self.app.conn.commit()
        self.app.delete_backup = False
        self.after_change(fids, ["case_text"])

    def after_change(self, fids, tables):
        """ Reload, refresh the host table cells and tell other dialogs. """

        self.load_cases()
        self.host.files_cases_changed(fids)
        self.cases_changed.emit(tables)
        self.fill_tree()

    # Context menu

    def tree_menu(self, position):
        selected = self.tree.itemAt(position)
        key = self.item_key(selected)
        fid = self.key_fid(key)
        caseid = self.item_caseid(selected)
        is_case = fid is None and caseid is not None and caseid != NO_CASE
        menu = self.menu()
        action_view = action_assign = action_remove = None
        action_rename = action_memo = action_delete = action_add_selected = None
        if fid is not None:
            action_view = menu.addAction(_("View file"))
            action_assign = menu.addAction(_("Assign to case"))
            if caseid is not None and caseid != NO_CASE:
                action_remove = menu.addAction(_("Remove from case"))
        action_new = menu.addAction(_("New case"))
        if is_case:
            action_rename = menu.addAction(_("Rename case"))
            action_memo = menu.addAction(_("Memo"))
            if self.host.visible_selected_rows():
                action_add_selected = menu.addAction(_("Assign selected table files to this case"))
            action_delete = menu.addAction(_("Delete case"))
        action_expand = menu.addAction(_("Expand all"))
        action_collapse = menu.addAction(_("Collapse all"))
        action = menu.exec(self.tree.mapToGlobal(position))
        if action is None:
            return
        if action == action_view:
            self.host.view_file(fid)
        elif action == action_assign:
            self.assign_dialog(self.selected_fids(fid))
        elif action == action_remove:
            self.remove_files_from_case(self.selected_fids(fid), caseid)
        elif action == action_new:
            self.add_case()
        elif action == action_rename:
            self.rename_case(caseid)
        elif action == action_memo:
            self.case_memo(caseid)
        elif action == action_add_selected:
            fids = [self.host.source[r]['id'] for r in self.host.visible_selected_rows()
                    if r < len(self.host.source)]
            self.assign_files_to_case(fids, caseid)
        elif action == action_delete:
            self.delete_case(caseid)
        elif action == action_expand:
            self.tree.expandAll()
        elif action == action_collapse:
            self.tree.collapseAll()
            self.tree.topLevelItem(0).setExpanded(True)

    def assign_dialog(self, fids):
        """ Ask for one or more cases and link the files to them. """

        if not fids or not self.cases:
            return
        choices = [{'name': c['name'], 'id': c['caseid']} for c in self.cases]
        ui = DialogSelectItems(self.app, choices, _("Assign files"), "multi")
        if not ui.exec():
            return
        for chosen in ui.get_selected() or []:
            self.assign_files_to_case(fids, chosen['id'])

    def add_case(self):
        """ New case with placeholders for the case attributes. """

        ui = DialogAddItemName(self.app, [{'name': c['name']} for c in self.cases], _("Case"),
                               _("Enter case name"))
        ui.exec()
        name = ui.get_new_name()
        if name is None or name.strip() == "":
            return
        name = name.strip()
        now = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
        owner = self.app.settings['codername']
        cur = self.app.conn.cursor()
        cur.execute("insert into cases (name,memo,owner,date) values(?,?,?,?)", [name, "", owner, now])
        caseid = cur.lastrowid
        cur.execute("select name from attribute_type where caseOrFile='case'")
        for att in cur.fetchall():
            cur.execute("insert into attribute(name,attr_type,value,id,date,owner) values (?,?,?,?,?,?)",
                        [att[0], "case", "", caseid, now, owner])
        self.app.conn.commit()
        self.app.delete_backup = False
        self.host.parent_text_edit.append(_("Case added: ") + name)
        self.cases_changed.emit(["cases", "attribute"])
        self.fill_tree()

    def rename_case(self, caseid):
        case_ = self.case_by_id(caseid)
        if case_ is None:
            return
        others = [{'name': c['name']} for c in self.cases if c['caseid'] != caseid]
        ui = DialogAddItemName(self.app, others, _("Rename case"), _("New case name"))
        ui.ui.lineEdit.setText(case_['name'])
        ui.exec()
        name = ui.get_new_name()
        if name is None or name.strip() == "" or name.strip() == case_['name']:
            return
        name = name.strip()
        cur = self.app.conn.cursor()
        cur.execute("update cases set name=? where caseid=?", [name, caseid])
        self.app.conn.commit()
        self.app.delete_backup = False
        self.host.parent_text_edit.append(_("Case renamed: ") + case_['name'] + " -> " + name)
        self.after_change(list(self.case_files.get(caseid, set())), ["cases"])

    def case_memo(self, caseid):
        case_ = self.case_by_id(caseid)
        if case_ is None:
            return
        ui = DialogMemo(self.app, _("Memo for case ") + case_['name'], case_['memo'],
                        entity_type="case", entity_id=caseid)
        ui.exec()
        if ui.memo == case_['memo']:
            return
        self.save_case_memo(caseid, ui.memo)

    def save_case_memo(self, caseid, memo: str):
        case_ = self.case_by_id(caseid)
        if case_ is None:
            return
        cur = self.app.conn.cursor()
        cur.execute("update cases set memo=? where caseid=?", [memo, caseid])
        self.app.conn.commit()
        self.app.delete_backup = False
        if memo != "":
            self.host.parent_text_edit.append(_("Memo for case ") + case_['name'])
        self.cases_changed.emit(["cases"])
        self.fill_tree()

    def delete_case(self, caseid):
        """ Delete the case, its file links and its attribute values, as in the Cases dialog. """

        case_ = self.case_by_id(caseid)
        if case_ is None:
            return
        ui = DialogConfirmDelete(self.app, _("Delete case") + ": " + case_['name'] + "\n" +
                                 _("Files are kept, only their link to this case is removed."))
        if not ui.exec():
            return
        fids = list(self.case_files.get(caseid, set()))
        cur = self.app.conn.cursor()
        cur.execute("delete from cases where caseid=?", [caseid])
        cur.execute("delete from case_text where caseid=?", [caseid])
        cur.execute("delete from attribute where id=? and attr_type='case'", [caseid])
        self.app.conn.commit()
        self.app.delete_backup = False
        if self.current_caseid == caseid:
            self.current_caseid = None
        self.host.parent_text_edit.append(_("Case deleted: ") + case_['name'])
        self.after_change(fids, ["cases", "case_text", "attribute"])
