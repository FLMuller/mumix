# chartdef -- the XY chart definition

One chart is one **tkv node**. xlw writes it to an Excel chart, `xlreader` fills one from
an Excel chart, and `svgchart` draws one. All three use this layout, so the picture in the
HTML report and the chart in the workbook come from the same definition.

Scope: **XY scatter charts only** (Excel's "Scatter" family: markers, straight lines,
smoothed lines, any mix per series). Other chart types, chart sheets and 3-D are not
defined here.

Version M01 m01.v01 (2026-10-31). Written from workbooks saved by Excel 16 and the OOXML
schema (ECMA-376 part 1, DrawingML charts). What was and was not checked against an
Excel-saved file is in section 9.

---------------------------------------------------------------------------------------

## 1. How a chart is stored

```python
xl = xlw()
xl.newbook('out/run.xlsx', 'Data')
chart = xl.chart('conc')              # a tkv node under the sheet's priv.charts
chart.title.text = 'Concentration'    # a leaf of the node 'title'
chart.xaxis.title.text = 'time (s)'
chart.yaxis.log = 10                  # log axis, base 10
add_series(chart, x='Data!$A$2:$A$100', y='Data!$B$2:$B$100', label='A')
place(chart, col=4, row=1)            # where it sits on the sheet
xl.save()
```

Two kinds of thing, as everywhere in this project:

* a **node** (a tkv child) holds a group of settings: `title`, `legend`, `xaxis`, ...
* a **record** (a `kv` stored as ONE leaf) holds a small flat set of fields that always
  travel together: `font`, `line`, `fill`, `marker`, `layout`. Write a record with
  `chart.title.font = rec(name='Calibri', height=14)` (see `rec` in xlchart) and read a
  field with `chart.title.font.height`.

A missing leaf means "use the default" (section 7); a leaf that is `None` is the same.
The node names below are all legal tkv names (none equals a tkv method name).

---------------------------------------------------------------------------------------

## 2. Records (kv) -- stated up front

Fields not listed stay at their default. Lengths are in points (pt), angles in degrees.

| record | fields | meaning |
|:--|:--|:--|
| `font` | `name`, `height`, `color`, `bold`, `ital`, `under` | `name` typeface ('Calibri'); `height` pt; `color` see 3; `bold`, `ital`, `under` booleans |
| `line` | `color`, `width`, `dash`, `none`, `cap` | `width` pt; `dash` one of solid, dot, dash, dashDot, longDash, longDashDot, sysDot, sysDash; `none` True = no line; `cap` flat, rnd, sq |
| `fill` | `color`, `none`, `alpha` | `none` True = no fill; `alpha` 0-100 (percent opaque) |
| `marker` | `symbol`, `size`, `fill`, `linecolor`, `linewidth` | `symbol` one of none, auto, circle, square, diamond, triangle, x, star, dot, dash, plus; `size` 2-72 pt; `fill` and `linecolor` colours; `linewidth` pt |
| `layout` | `x`, `y`, `w`, `h` | fractions 0-1 of the chart area, measured from its top-left corner; any may be absent (`w` and `h` default to automatic) |
| `anchor` | `col`, `colOff`, `row`, `rowOff`, `col2`, `colOff2`, `row2`, `rowOff2` | cell anchor on the sheet: zero-based cell and EMU offset (12700 EMU = 1 pt), top-left then bottom-right |

## 3. Colour strings

A colour is one string:

* `RRGGBB` six hex digits (`'4472C4'`), or any form `xlstyle.color2hex` accepts;
* `theme:NAME[:lumMod[:lumOff]]` a theme colour as Excel writes them, for example
  `theme:tx1:65000:35000` or `theme:accent1`; the two numbers are OOXML thousandths of
  a percent. Written back unchanged; the HTML/SVG side resolves them with the Office
  palette (section 8);
* `sys:NAME[:RRGGBB]` a system colour, for example `sys:windowText:000000`.

xlw writes `RRGGBB` as `srgbClr`. Workbooks made by xlw carry no theme part, so xlw never
invents a `theme:` colour by itself; it passes through the ones it read.

---------------------------------------------------------------------------------------

## 4. The chart node

| leaf or node | kind | default | meaning (OOXML element) |
|:--|:--|:--|:--|
| `style` | leaf | `'lineMarker'` | scatter style of the chart: lineMarker, line, marker, smooth, smoothMarker, none (`c:scatterStyle`). Each series can still choose its own line, marker and smoothing |
| `blanks` | leaf | `'gap'` | empty cells are drawn as gap, zero or span (`c:dispBlanksAs`) |
| `visibleonly` | leaf | `True` | plot only visible cells (`c:plotVisOnly`) |
| `title` | node, **Text** | absent | chart title; absent = no title (`c:autoTitleDeleted` 1) |
| `legend` | node, **Legend** | absent | absent = no legend |
| `xaxis`, `yaxis` | node, **Axis** | see Axis | the primary pair (`c:valAx` bottom, left) |
| `x2axis`, `y2axis` | node, **Axis** | absent | the secondary pair; made when a series has `axis = 2` |
| `plotarea` | node | no fill, no line | `fill` and `line` records, `layout` record (`c:plotArea/c:spPr`) |
| `chartarea` | node | white fill, light grey line | `fill`, `line`, `font` (the default text of the chart), `rounded` bool (`c:chartSpace/c:spPr`, `c:txPr`, `c:roundedCorners`) |
| `series` | node | empty | children `s1`, `s2`, ...; insertion order is plot order and legend order |
| `anchor` | leaf, record | beside the data | where the chart sits (section 2) |

### Text node (title of the chart or of an axis)

| leaf | default | meaning |
|:--|:--|:--|
| `text` | none | a string; a list of runs `[(text, props), ...]` for mixed formatting, where `props` is a dict with any of `baseline` (percent: 30 superscript, -25 subscript), `bold`, `ital`, `under`, `height`, `color`, `name`. Absent on the chart title = Excel's automatic title |
| `font` | Calibri 14, color `595959` (axis titles 10) | record |
| `rot` | 0 for the chart and X axis titles, -90 for a Y axis title | degrees |
| `overlay` | `False` | the title floats over the plot |
| `layout` | automatic | record (manual position) |

### Legend node

| leaf | default | meaning |
|:--|:--|:--|
| `pos` | `'r'` | l, r, t, b or tr |
| `overlay` | `False` | |
| `font` | Calibri 9, `595959` | record |
| `fill`, `line` | none, none | records |
| `layout` | automatic | record |
| `hide` | `[]` | list of 1-based series numbers whose legend entry is removed |

### Axis node

Axes are value axes (scatter). `xaxis` is the horizontal one, `yaxis` the vertical one.

| leaf or node | default | meaning (OOXML element) |
|:--|:--|:--|
| `min`, `max` | auto | axis limits (`c:scaling/c:min`, `c:max`) |
| `major`, `minor` | auto | tick spacing in axis units (`c:majorUnit`, `c:minorUnit`) |
| `log` | `None` (linear) | log base, for example 10 (`c:logBase`); data and limits must be > 0 |
| `reverse` | `False` | largest value first (`c:orientation` maxMin) |
| `visible` | `True` | `False` hides the axis (`c:delete` 1) |
| `title` | absent | **Text** node |
| `gridmajor`, `gridminor` | major: `line(color='D9D9D9', width=0.75)` on the primary axes, none on the secondary; minor: none | line records; a record with `none=True` switches that gridline off (`c:majorGridlines`, `c:minorGridlines`). A tkv leaf cannot hold `None`: writing `None` deletes the leaf |
| `numfmt` | none = linked to the source cells | number format code of the tick labels, e.g. `'0.00'` (`c:numFmt`) |
| `tickmajor`, `tickminor` | `'out'`, `'none'` | none, in, out, cross (`c:majorTickMark`, `c:minorTickMark`) |
| `ticklabels` | `'nextTo'` | nextTo, low, high, none (`c:tickLblPos`) |
| `crossesat` | `None` | **where the OTHER axis crosses this one**, in this axis's units (`c:crossesAt`, stored in the other axis's element, see 6) |
| `crosses` | `'autoZero'` | when `crossesat` is None: autoZero, min, max (`c:crosses`) |
| `line` | `line(color='BFBFBF', width=0.75)` | axis line record |
| `font` | Calibri 9, `595959` | tick label font record |
| `labelrot` | automatic | tick label angle, degrees (`a:bodyPr rot`) |
| `between` | `'midCat'` | crossBetween; scatter charts always use midCat |

### Series node  (`chart.series.s1`, `s2`, ...)

| leaf or node | default | meaning (OOXML element) |
|:--|:--|:--|
| `label` | none | series name, literal text (`c:tx/c:v`) |
| `labelref` | none | series name from a cell, `'Data!$B$1'` (`c:tx/c:strRef`); wins over `label` |
| `x`, `y` | required | data: a cell range `'Sheet!$A$2:$A$100'` (`c:numRef/c:f`) or a list of numbers (`c:numLit`) |
| `axis` | `1` | 1 primary axes, 2 secondary axes |
| `line` | palette colour, 2.25 pt | record; `none=True` for markers only |
| `marker` | `symbol='none'` for a chart style `line`, else `'circle'`, size 5, palette colour | record |
| `smooth` | `False` | smoothed line (`c:smooth`) |
| `trend` | node, absent | **Trendline** |
| `xerr`, `yerr` | node, absent | **ErrorBars** |
| `labels` | node, absent | **DataLabels** |

Series colours cycle through `4472C4 ED7D31 A5A5A5 FFC000 5B9BD5 70AD47` (Office 2013).

### Trendline node

| leaf | default | meaning |
|:--|:--|:--|
| `fit` | `'linear'` | linear, exp, log, poly, power, movingAvg (`c:trendlineType`). Not called `type`: that is a tkv method name |
| `order` | 2 | polynomial order, 2-6 (`c:order`, poly only) |
| `period` | 2 | moving-average period (`c:period`, movingAvg only) |
| `forward`, `backward` | 0 | extend by this many x units (`c:forward`, `c:backward`) |
| `intercept` | `None` | force the intercept (`c:intercept`) |
| `rsq`, `eq` | `False` | show R-squared, show the equation (`c:dispRSqr`, `c:dispEq`) |
| `label` | none | name in the legend (`c:name`) |
| `line` | series colour, 1.5 pt, dash | record |
| `numfmt`, `font`, `layout` | none | of the equation label (`c:trendlineLbl`) |

### ErrorBars node  (`xerr` or `yerr`)

| leaf | default | meaning |
|:--|:--|:--|
| `mode` | `'fixed'` | fixed, percentage, stddev, stderr, custom (`c:errValType`). Not called `type`: that is a tkv method name |
| `value` | 1 | the amount for fixed, percentage (percent), stddev (multiples) (`c:val`) |
| `dir` | `'both'` | both, plus, minus (`c:errBarType`) |
| `plus`, `minus` | none | custom amounts: a cell range or a list (`c:plus`, `c:minus`) |
| `endcap` | `True` | draw end caps (`c:noEndCap` 0) |
| `line` | series colour, 0.75 pt | record |

### DataLabels node

| leaf | default | meaning |
|:--|:--|:--|
| `showy`, `showx`, `showname`, `showkey` | `False` | what the label shows (`c:showVal`, `c:showCatName`, `c:showSerName`, `c:showLegendKey`) |
| `pos` | automatic | r, l, t, b, ctr (`c:dLblPos`) |
| `numfmt` | none | format code (`c:numFmt`) |
| `font` | none | record |

---------------------------------------------------------------------------------------

## 5. Defaults at a glance

A chart made by `xl.chart('name')` plus `add_series` draws: style lineMarker, each series
a coloured 2.25 pt line with 5 pt circle markers, white chart area with a light border,
major gridlines on both axes, axes with outward ticks and labels beside them, no title,
no legend. A chart with more than one series should get a legend; xlchart does **not**
add one by itself (set `chart.legend.pos = 'r'`).

---------------------------------------------------------------------------------------

## 6. OOXML emission rules -- the finicky details

Excel refuses or "repairs" a chart whose elements are in the wrong order or that lacks an
element it requires, and it says little about why. These are the rules xlchart follows;
the order was read from charts saved by Excel 16 and checked against the schema.

* `c:chartSpace` children: `date1904`, `lang`, `roundedCorners`, `chart`, `spPr`, `txPr`,
  `printSettings` (the `mc:AlternateContent` style wrapper is left out).
* `c:chart`: `title`, `autoTitleDeleted`, `plotArea`, `legend`, `plotVisOnly`,
  `dispBlanksAs`. With no title, `autoTitleDeleted` is 1.
* `c:plotArea`: `layout` (present, empty), the `c:scatterChart` of the primary axes, the
  `c:scatterChart` of the secondary axes (if any), then ALL the `c:valAx` elements, then
  `spPr`. A scatter chart has TWO `valAx` (x first, then y), never a `catAx`.
* `c:scatterChart`: `scatterStyle`, `varyColors` (0), the series, `dLbls`, then exactly
  two `axId`: the x axis id first, the y axis id second.
* `c:ser`: `idx`, `order`, `tx`, `spPr`, `marker`, `dPt`, `dLbls`, `trendline`, `errBars`
  (x before y), `xVal`, `yVal`, `smooth`. `idx` and `order` are unique across the chart.
* `c:marker` with `symbol none` has no `size` and no `spPr`.
* `c:valAx`: `axId`, `scaling`, `delete`, `axPos`, `majorGridlines`, `minorGridlines`,
  `title`, `numFmt`, `majorTickMark`, `minorTickMark`, `tickLblPos`, `spPr`, `txPr`,
  `crossAx`, `crosses` or `crossesAt`, `crossBetween`, `majorUnit`, `minorUnit`.
* `c:scaling`: `logBase`, `orientation`, `max`, `min` (note: max before min).
* `c:crosses` / `c:crossesAt` in the element of axis A say where A crosses its `crossAx`.
  So the `crossesat` the user sets on the Y axis ("the X axis crosses at Y = 5") is
  written into the **X** axis element. xlchart does the swap; the reader undoes it.
* `axPos`: `b` for the primary x axis, `l` for the primary y axis, `t` and `r` for the
  secondary pair. The secondary y axis has `crosses max` and the secondary x axis is
  `delete 1` unless the user made it visible.
* Axis ids are positive integers, unique in the chart. xlchart uses 500000001 and
  500000002 (primary x, y) and 500000003 and 500000004 (secondary x, y).
* The names `type`, `name`, `kind`, `count`, `keys` ... are tkv method names and cannot be
  node or leaf names; the definition avoids them (`fit`, `mode`, `label`).
* A title with text writes `c:tx/c:rich` (`a:bodyPr rot`, `a:lstStyle`, `a:p` with one
  `a:pPr/a:defRPr` and one `a:r` per run); a title without text writes only
  `overlay`, `spPr`, `txPr`.
* A series name that is a literal is `c:tx/c:v`; from a cell it is `c:tx/c:strRef`.
* A data reference is `c:numRef` with `c:f` (the range) and `c:numCache` (`formatCode`,
  `ptCount`, one `c:pt` per number; blank cells have no `pt`). The cache lets viewers
  that do not recalculate show the chart.
* The sheet name in a range is quoted with single quotes when it has anything but
  letters, digits and underscores (`'My Sheet'!$A$1`), with `'` doubled inside.
* On the sheet: the worksheet root declares `xmlns:r`; `<drawing r:id="rId1"/>` follows
  `sheetData`; the drawing part holds one `xdr:twoCellAnchor` per chart; content types
  and relationships as in xlparts.
* Only `0..8` and `11`, `12`, `14..31` are control characters XML 1.0 cannot carry; all
  text is passed through `xlstyle.xml_escape`, which removes them.

---------------------------------------------------------------------------------------

## 7. Axis scaling when the limits are left automatic

Excel does not store the limits it chose, so a drawing has to choose them the same way.
svgchart uses these rules (Microsoft's published description of the automatic scale):

* Linear axis, data range `[lo, hi]`, `d = hi - lo`: the working limits are `hi + 0.05 d`
  and `lo - 0.05 d`; if `lo >= 0` and the lower limit is below `5/6` of the upper limit,
  the lower limit becomes 0.
* Major unit: the first of `1, 2, 5` times a power of ten that gives at most 10 intervals.
* The axis then runs from the lower limit rounded down to a multiple of the major unit to
  the upper limit rounded up to one.
* Log axis: limits are the powers of the base that enclose the data; major ticks at each
  power, minor ticks at 2..9 times a power for base 10.

These rules reproduce what Excel draws for ordinary data but are an approximation: set
`min`, `max` and `major` on an axis when the picture must match exactly.

---------------------------------------------------------------------------------------

## 8. Theme colours when drawing

`theme:tx1` is black, `bg1` white, `tx2` 44546A, `bg2` E7E6E6, `accent1`..`accent6` as the
palette in section 4, `hlink` 0563C1, `folHlink` 954F72. `lumMod` and `lumOff` brighten:
`c' = c * lumMod/100000 + 255 * lumOff/100000` per channel (the usual simplification of the
HSL operation, exact for greys, which is what chart text and gridlines use).

---------------------------------------------------------------------------------------

## 9. Status: written, read, drawn, and what was checked

| feature | xlw writes | xlreader reads | svgchart draws | checked against an Excel-saved file |
|:--|:--:|:--:|:--:|:--|
| scatter styles, markers, lines, smooth | yes | yes | yes | yes (4 charts) |
| series names literal / from cells, data ranges + cache | yes | yes | yes | yes |
| chart and axis titles with runs | yes | yes | yes | yes |
| legend with position and manual layout | yes | yes | yes | yes |
| major gridlines, tick marks, tick label position | yes | yes | yes | yes |
| trendline with equation and R-squared | yes | yes | yes | yes (1 chart) |
| secondary axes | yes | yes | yes | no (none supplied) |
| log axes, fixed min / max / units, reverse | yes | yes | yes | no |
| axis crossing (`crossesat`) | yes | yes | yes | no |
| error bars | yes | yes | yes | no |
| data labels | yes | yes | partly | no |
| minor gridlines | yes | yes | yes | no |
| display units, data table | no | no | no | -- |

"No" means the XML follows the schema order and the same pattern as the checked features,
but no Excel-saved file with that feature was available. Those are the first things to
look at if Excel repairs a workbook, and the reference workbook asked for in the report
would settle them.

Reading Excel files: the reader skips `mc:AlternateContent`, `c:extLst`, `c:userShapes`,
`c14`/`c16` extension elements and the chart `style`/`colors` parts quietly, and lists
everything else it does not map in an "unmapped" report.
