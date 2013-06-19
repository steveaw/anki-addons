import time

from aqt import *
from anki.hooks import addHook

# Some useful columns to have
_usefulColumns = [('cfirst', "First review"),
                ('clast', "Last review"),
                ('cavtime', "Time (Average)"),
                ('ctottime', "Time (Total)"),
                ('ntags', "Tags")]



# Dictionary of field names indexed by "type" name. Used to figure out if
# the requested column is a note field.
_fieldTypes = {}

# Dictionary of dictionaries to get position for field in model.
# { mid -> {fldName -> pos}}
# We build this dictionary once to avoid needlessly finding the field order
# for every single row when sorting. It's significantly faster that way.
_modelFieldPos = {}


# def myColumnData(self, index):
#     if type in _fieldTypes:
#         field = _fieldTypes[type]
#         if field in c.note().keys():
#             return c.note()[field]



# def my_order(self, order):
         
#     if type in _fieldTypes:
#         fldName = _fieldTypes[type]
#         sort = "(select valueForField(mid, flds, '%s') from notes where id = c.nid)" % fldName
 

# def mySetupColumns(self):
#     global _customColumns
#     global _fieldTypes
#     global _modelFieldPos
# 
#     fieldColumns = []
#     for model in mw.col.models.all():
#         # For some reason, some mids return as unicode, so convert to int
#         mid = int(model['id'])
#         _modelFieldPos[mid] = {}
#         for field in model['flds']:
#             name = field['name']
#             ord = field['ord']
#             type = "_field_"+name #prefix to avoid potential clashes
#             _modelFieldPos[mid][name] = ord
#             if (type, name) not in fieldColumns:
#                 fieldColumns.append((type, name))
#                 _fieldTypes[type] = name
# 
#     _customColumns = _usefulColumns  + fieldColumns
#     self.columns.extend(_customColumns)


# def myOnHeaderContext(self, pos):
#     gpos = self.form.tableView.mapToGlobal(pos)
#     
#     m = QMenu()
#     # Sub-menu containing every uniquely named field in the collection.
#     fm = QMenu("Fields")
#     
#     def addCheckableAction(menu, type, name):
#         a = menu.addAction(name)
#         a.setCheckable(True)
#         a.setChecked(type in self.model.activeCols)
#         a.connect(a, SIGNAL("toggled(bool)"),
#                   lambda b, t=type: self.toggleField(t))
#     
#     for item in self.columns:
#         type, name = item
#         if type in _fieldTypes:
#             addCheckableAction(fm, type, name)
#         else:
#             addCheckableAction(m, type, name)
#     
#     m.addMenu(fm)
#     m.exec_(gpos)



def valueForField(mid, flds, fldName):
    """
    SQLite function to get the value of a field, given a field name.
    
    mid is the model id. The model contains the definition of a note,
    including the names of all fields.
    
    flds contains the text of all fields, delimited by the character
    "x1f". We split this and index into it according to a precomputed
    index for the model (mid) and field name (fldName).
    
    fldName is the field name we are after.
    """

    index = _modelFieldPos.get(mid).get(fldName, None)
    if index:
        fieldsList = flds.split("\x1f", index)
        return fieldsList[index]

def onLoad():
    # Create a new SQL function that we can use in our queries.
    mw.col.db._db.create_function("valueForField", 3, valueForField)

def onAdvBrowserLoad():
    print "advanced_browser.py -> onAdvBrowserLoad"
    
        
    global _fieldTypes
    global _modelFieldPos

    for model in mw.col.models.all():
        # For some reason, some mids return as unicode, so convert to int
        mid = int(model['id'])
        _modelFieldPos[mid] = {}
        for field in model['flds']:
            name = field['name']
            ord = field['ord']
            type = "_field_"+name #prefix to avoid potential clashes
            _modelFieldPos[mid][name] = ord
            if type not in _fieldTypes:
                _fieldTypes[type] = name
                # TODO: Add CustomColumn here!
                
    createCustomColumns()
    

def createCustomColumns():
    from advanced_browser_core import CustomColumn, addCustomColumn
    
    # First review
    def cFirstOnData(c, n, t):
        first = mw.col.db.scalar(
            "select min(id) from revlog where cid = ?", c.id)
        if first:
            return time.strftime("%Y-%m-%d", time.localtime(first / 1000))
   
    addCustomColumn(CustomColumn(
        key = 'cfirst',
        name = 'First Review',
        onData = cFirstOnData,
        onSort = lambda: "(select min(id) from revlog where cid = c.id)"
    ))
    #---------
    
    # Last review
    def cLastOnData(c, n, t):
        last = mw.col.db.scalar(
            "select max(id) from revlog where cid = ?", c.id)
        if last:
            return time.strftime("%Y-%m-%d", time.localtime(last / 1000))
   
    addCustomColumn(CustomColumn(
        key = 'clast',
        name = 'Last Review',
        onData = cLastOnData,
        onSort = lambda: "(select max(id) from revlog where cid = c.id)"
    ))
    #---------
    
    # Average time
    def cAvgtimeOnData(c, n, t):
        avgtime = mw.col.db.scalar(
            "select avg(time) from revlog where cid = ?", c.id)
        if avgtime:
            return str(round(avgtime / 1000, 1)) + "s"
    
    addCustomColumn(CustomColumn(
        key = 'cavgtime',
        name = 'Time (Average)',
        onData = cAvgtimeOnData,
        onSort = lambda: "(select avg(time) from revlog where cid = c.id)"
    ))    
    #---------

    # Total time
    def cTottimeOnDAta(c, n, t):
        tottime = mw.col.db.scalar(
            "select sum(time) from revlog where cid = ?", c.id)
        if tottime:
            return str(round(tottime / 1000, 1)) + "s"

    addCustomColumn(CustomColumn(
        key = 'ctottime',
        name = 'Time (Total)',
        onData = cTottimeOnDAta,
        onSort = lambda: "(select sum(time) from revlog where cid = c.id)"
    ))
    #---------
    
    # Tags
    addCustomColumn(CustomColumn(
        key = 'ntags',
        name = 'Tags',
        onData = lambda c, n, t: " ".join(str(tag) for tag in n.tags),
        onSort = lambda: "n.tags"
    ))
    #---------
    
    # Note fields
    def fldOnData(c, n, t):
        field = _fieldTypes[t]
        if field in c.note().keys():
            return c.note()[field]

    def fldOnSort(type):
        if type in _fieldTypes:
            fldName = _fieldTypes[type]
            return ("(select valueForField(mid, flds, '%s') from notes "
                    "where id = c.nid)" % fldName)
        
    for type, name in _fieldTypes.iteritems():
        addCustomColumn(CustomColumn(
            key = type,
            name = name,
            onData = fldOnData,
            onSort = fldOnSort
        ))
    #---------
    
addHook("profileLoaded", onLoad)
addHook("advBrowserLoad", onAdvBrowserLoad)