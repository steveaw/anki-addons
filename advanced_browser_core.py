# -*- coding: utf-8 -*-
# Version: 0.1alpha1
# See github page to report issues or to contribute:
# https://github.com/hssm/anki-addons

from aqt import *
from aqt.browser import DataModel, Browser
from anki.hooks import wrap, addHook, runHook
from anki.find import Finder

CONF_KEY = 'advbrowse_activeCols'

origColumnData = DataModel.columnData
orig_order = Finder._order

# CustomColumn objects maintained by this add-on. Indexed by CustomColumn.key.
_advColumns = {}

# Later on, we combine all custom columns for easier iteration.
_customColumns = []

    
class CustomColumn:
    """A custom browser column.
    
    key = Internally used name to identify the column.   
    
    name = Name of column, visible to the user.
    
    onData = Function that returns an SQL query as a string. The query
    must return a scalar result.
    
    onSort = Optional function that returns an SQL query as a string to
    sort the column. This query will be used as the "where" clause of
    a larger query.
    In this query, you have the names "c" and "n" to refer to cards and
    notes, respectively. See find.py::_query for reference.
    E.g. : return "(select min(id) from revlog where cid = c.id)""
    """
    def __init__(self, key, name, onData, onSort=None):
        self.type = key
        self.name = name
        self.onData = onData
        self.onSort = onSort

    
def addCustomColumn(cc):
    """Add a CustomColumn object to be maintained by this add-on."""
    
    global _advColumns
    _advColumns[cc.type] = cc


def myDataModel__init__(self, browser):
    """Load any custom columns that were saved in a previous session."""
    
    # First, we make sure those columns are still valid. If not, we ignore
    # them. This is to guard against the event that we remove or rename a
    # column (i.e., a note field). Also make sure the sortType is set to a
    # valid column.
    
    sortType = mw.col.conf['sortType']
    validSortType = False
    custCols = mw.col.conf.get(CONF_KEY, [])
    
    for custCol in custCols:
        for type, name in _customColumns:
            if custCol == type and custCol not in self.activeCols:
                self.activeCols.append(custCol)
            if sortType == type:
                validSortType = True
    
    if not validSortType:
        mw.col.conf['sortType'] = 'noteCrt'


def mySetupColumns(self):
    """Build a list of candidate columns. We extend the internal
    self.columns list with our custom types."""
    
    global _customColumns
    for type in _advColumns:
        _customColumns.append((_advColumns[type].type, _advColumns[type].name))

    self.columns.extend(_customColumns)
    
def myOnHeaderContext(self, pos):
    gpos = self.form.tableView.mapToGlobal(pos)
    m = QMenu()
    
    # Sub-menu containing every uniquely named field in the collection.
    fm = QMenu("Fields")
    
    def addCheckableAction(menu, type, name):
        a = menu.addAction(name)
        a.setCheckable(True)
        a.setChecked(type in self.model.activeCols)
        a.connect(a, SIGNAL("toggled(bool)"),
                  lambda b, t=type: self.toggleField(t))
    
    for item in self.columns:
        type, name = item
        if type in _advColumns:
            # TODO: put them in a better place !
            addCheckableAction(fm, type, name)
        else:
            addCheckableAction(m, type, name)
    
    m.addMenu(fm)
    m.exec_(gpos)


def myCloseEvent(self, evt):
    """Remove our columns from self.model.activeCols when closing.
    Otherwise, Anki would save them to the equivalent in the collection
    conf, which might have ill effects elsewhere. We save our custom
    types in a custom conf item instead."""
    
    #sortType = mw.col.conf['sortType']
    # TODO: should we avoid saving the sortType? We will continue to do
    # so unless a problem with doing so becomes evident.
        
    customCols = []
    origCols = []
    
    for col in self.model.activeCols:
        isOrig = True
        for custType, custName in _customColumns:
            if col == custType:
                customCols.append(col)
                isOrig = False
                break
        if isOrig:
            origCols.append(col)

    self.model.activeCols = origCols
    mw.col.conf[CONF_KEY] = customCols
    
    
def myColumnData(self, index):
    # Try to handle built-in Anki column
    returned = origColumnData(self, index)
    if returned:
        return returned
    
    # If Anki can't handle it, it must be one of ours.
    
    col = index.column()
    type = self.columnType(col)
    c = self.getCard(index)
    n = c.note()
    
    if type in _advColumns:
        return _advColumns[type].onData(c, n, type)

def my_order(self, order):
    # This is pulled from the original _order() -----------------------
    if not order:
        return "", False
    elif order is not True:
        # custom order string provided
        return " order by " + order, False
    # use deck default
    type = self.col.conf['sortType']
    sort = None
    # -----------------------------------------------------------------
    
    if type in _advColumns:
        sort = _advColumns[type].onSort(type)
    
    if not sort:
        # If we couldn't sort it, it must be a built-in column. Handle
        # it internally.
        return orig_order(self, order)
    
    # This is also from the original _order()
    return " order by " + sort, self.col.conf['sortBackwards']



DataModel.__init__ = wrap(DataModel.__init__, myDataModel__init__)
DataModel.columnData = myColumnData
Browser.setupColumns = wrap(Browser.setupColumns, mySetupColumns)
Browser.onHeaderContext = myOnHeaderContext
Browser.closeEvent = wrap(Browser.closeEvent, myCloseEvent, "before")
Finder._order = my_order

def onLoad():
    runHook("advBrowserLoad")
    
# Ensure other add-ons don't try to use this one until it has loaded.
addHook("profileLoaded", onLoad)