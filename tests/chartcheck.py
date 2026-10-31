"""
chartcheck -- shared checks for the chart and package tests (a test helper, not a suite).

order_errors(root)       every violation of the ECMA-376 child order in an element tree
package_errors(filename) content types and relationships of an .xlsx package

ORDER holds the child sequences of the schema for every element xlchart writes, typed in
independently of the code under test; the same tables are run over the charts Excel
itself wrote (b_xlchart), which is what makes them trustworthy.
"""

import os
import zipfile
import xml.etree.ElementTree as ET

__all__ = ['ORDER', 'local', 'order_errors', 'package_errors']

# ECMA-376 child sequences (local names). An element absent from this table is not
# checked; a child absent from its parent's list is an error.
ORDER = {
    'chartSpace': ['date1904', 'lang', 'roundedCorners', 'AlternateContent', 'style',
                   'clrMapOvr', 'pivotSource', 'protection', 'chart', 'spPr', 'txPr',
                   'externalData', 'printSettings', 'userShapes', 'extLst'],
    'chart': ['title', 'autoTitleDeleted', 'pivotFmts', 'view3D', 'floor', 'sideWall',
              'backWall', 'plotArea', 'legend', 'plotVisOnly', 'dispBlanksAs',
              'showDLblsOverMax', 'extLst'],
    'plotArea': ['layout', 'scatterChart', 'valAx', 'dTable', 'spPr', 'extLst'],
    'scatterChart': ['scatterStyle', 'varyColors', 'ser', 'dLbls', 'axId', 'extLst'],
    'ser': ['idx', 'order', 'tx', 'spPr', 'marker', 'dPt', 'dLbls', 'trendline',
            'errBars', 'xVal', 'yVal', 'smooth', 'extLst'],
    'valAx': ['axId', 'scaling', 'delete', 'axPos', 'majorGridlines', 'minorGridlines',
              'title', 'numFmt', 'majorTickMark', 'minorTickMark', 'tickLblPos', 'spPr',
              'txPr', 'crossAx', 'crosses', 'crossesAt', 'crossBetween', 'majorUnit',
              'minorUnit', 'dispUnits', 'extLst'],
    'scaling': ['logBase', 'orientation', 'max', 'min', 'extLst'],
    'title': ['tx', 'layout', 'overlay', 'spPr', 'txPr', 'extLst'],
    'legend': ['legendPos', 'legendEntry', 'layout', 'overlay', 'spPr', 'txPr', 'extLst'],
    'legendEntry': ['idx', 'delete', 'txPr', 'extLst'],
    'marker': ['symbol', 'size', 'spPr', 'extLst'],
    'trendline': ['name', 'spPr', 'trendlineType', 'order', 'period', 'forward',
                  'backward', 'intercept', 'dispRSqr', 'dispEq', 'trendlineLbl', 'extLst'],
    'trendlineLbl': ['layout', 'tx', 'numFmt', 'spPr', 'txPr', 'extLst'],
    'errBars': ['errDir', 'errBarType', 'errValType', 'noEndCap', 'plus', 'minus', 'val',
                'spPr', 'extLst'],
    'dLbls': ['dLbl', 'delete', 'numFmt', 'spPr', 'txPr', 'dLblPos', 'showLegendKey',
              'showVal', 'showCatName', 'showSerName', 'showPercent', 'showBubbleSize',
              'separator', 'showLeaderLines', 'leaderLines', 'extLst'],
    'manualLayout': ['layoutTarget', 'xMode', 'yMode', 'wMode', 'hMode', 'x', 'y', 'w',
                     'h', 'extLst'],
    'numRef': ['f', 'numCache', 'extLst'],
    'numCache': ['formatCode', 'ptCount', 'pt', 'extLst'],
    'numLit': ['formatCode', 'ptCount', 'pt', 'extLst'],
    'strRef': ['f', 'strCache', 'extLst'],
    'xVal': ['numRef', 'numLit', 'strRef', 'strLit', 'multiLvlStrRef'],
    'yVal': ['numRef', 'numLit'],
    'plus': ['numRef', 'numLit'],
    'minus': ['numRef', 'numLit'],
    'spPr': ['xfrm', 'custGeom', 'prstGeom', 'noFill', 'solidFill', 'gradFill',
             'blipFill', 'pattFill', 'grpFill', 'ln', 'effectLst', 'effectDag', 'scene3d',
             'sp3d', 'extLst'],
    'ln': ['noFill', 'solidFill', 'gradFill', 'pattFill', 'prstDash', 'custDash', 'round',
           'bevel', 'miter', 'headEnd', 'tailEnd', 'extLst'],
    'rich': ['bodyPr', 'lstStyle', 'p'],
    'txPr': ['bodyPr', 'lstStyle', 'p'],
    'wsDr': ['twoCellAnchor', 'oneCellAnchor', 'absoluteAnchor'],
    'twoCellAnchor': ['from', 'to', 'graphicFrame', 'sp', 'grpSp', 'cxnSp', 'pic',
                      'contentPart', 'clientData'],
    'from': ['col', 'colOff', 'row', 'rowOff'],
    'to': ['col', 'colOff', 'row', 'rowOff'],
}


def local(tag):
    return tag.rsplit('}', 1)[-1]


def order_errors(root):
    """Every violation of ORDER inside an element tree, as readable strings."""
    errors = []
    for element in root.iter():
        name = local(element.tag)
        if name not in ORDER:
            continue
        sequence = ORDER[name]
        last = -1
        for child in element:
            child_name = local(child.tag)
            if child_name not in sequence:
                errors.append(f'{child_name} is not allowed inside {name}')
                continue
            position = sequence.index(child_name)
            if position < last:
                errors.append(f'{child_name} comes too late inside {name}')
            last = max(last, position)
    return errors


def package_errors(filename):
    """Content types and relationships of a package: every part has a content type, every
    relationship target exists, every relationship id is unique per part."""
    problems = []
    with zipfile.ZipFile(filename) as archive:
        names = set(archive.namelist())
        types = ET.fromstring(archive.read('[Content_Types].xml'))
        defaults = {item.get('Extension') for item in types if local(item.tag) == 'Default'}
        overrides = {item.get('PartName').lstrip('/') for item in types
                     if local(item.tag) == 'Override'}
        for name in names:
            if name == '[Content_Types].xml':
                continue
            if name not in overrides and name.rsplit('.', 1)[-1] not in defaults:
                problems.append(f'no content type for {name}')
        for override in overrides:
            if override not in names:
                problems.append(f'content type for a missing part {override}')
        for name in names:
            if not name.endswith('.rels'):
                continue
            base = os.path.dirname(os.path.dirname(name))
            ids = set()
            for rel in ET.fromstring(archive.read(name)):
                if rel.get('Id') in ids:
                    problems.append(f'duplicate {rel.get("Id")} in {name}')
                ids.add(rel.get('Id'))
                target = os.path.normpath(os.path.join(base, rel.get('Target')))
                if rel.get('TargetMode') != 'External' \
                        and target.replace('\\', '/') not in names:
                    problems.append(f'{name}: target {target} does not exist')
    return problems
