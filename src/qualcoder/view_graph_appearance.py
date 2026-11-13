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

Authors: Colin Curtain C, Kai Dröge, Justin Missaghieh--Poncet, Lorenzo Salomón
https://github.com/ccbogel/QualCoder
https://qualcoder.wordpress.com/
https://qualcoder-org.github.io
https://qualcoder.org/
"""

from collections import OrderedDict
import logging
import math
import sqlite3
import qtawesome as qta  # see: https://pictogrammers.com/library/mdi/

from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtWidgets import QDialog

from .color_selector import DialogColorSelect, TextColor
from .GUI.ui_dialog_graph_appearance import Ui_Dialog_graph_appearance
from .helpers import Message
from .select_items import DialogSelectItems

logger = logging.getLogger(__name__)

# Graph item classes are imported inside the functions that use them, because view_graph imports this module.

# --- node shapes, frequency sizes and line widths 2026-11-12 ---
NODE_SHAPES = ("rectangle", "icon", "ellipse", "circle")
SIZE_MODES = ("none", "branch", "project")
NODE_FONT_SIZES = (8, 10, 12, 14, 16, 18, 20)
DEFAULT_NODE_FONT_SIZE = 9
DEFAULT_LINE_WIDTH = 2
MIN_LINE_WIDTH = 1.0
MAX_LINE_WIDTH = 6.0
NODE_CORNER_RADIUS = 3
ON_CANVAS_TEXT_COLOR = "#202020"
HALO_COLOR = QtGui.QColor(255, 255, 255, 235)
HALO_WIDTH = 3.0


def node_shape_names():
    """ Display names of the node shapes. """
    return {"rectangle": _("Rectangle"), "icon": _("Color icon and name"),
            "ellipse": _("Ellipse"), "circle": _("Circle with name below")}


def size_mode_names():
    """ Display names of the size and line width modes. """
    return {"none": _("No adjustment"), "branch": _("Category or parent code total"),
            "project": _("Project total")}


def frequency_font_size(ratio):
    """ Map a frequency share (0-1) to one of NODE_FONT_SIZES; square root keeps the area proportional. """
    ratio = max(0.0, min(1.0, ratio))
    return NODE_FONT_SIZES[int(round(math.sqrt(ratio) * (len(NODE_FONT_SIZES) - 1)))]


def frequency_line_width(ratio):
    """ Map a frequency share (0-1) to a line width between MIN_LINE_WIDTH and MAX_LINE_WIDTH. """
    ratio = max(0.0, min(1.0, ratio))
    width = MIN_LINE_WIDTH + (MAX_LINE_WIDTH - MIN_LINE_WIDTH) * math.sqrt(ratio)
    return round(width * 2) / 2


HALO_CHUNK_GLYPHS = 16  # filling one shape made of thousands of overlapping glyph outlines takes seconds


def text_glyph_chunks(text_item):
    """ Glyph outlines in groups of a few glyphs, at the positions the text layout really draws them,
    so hinting and screen scaling match. """

    chunks = []
    chunk = QtGui.QPainterPath()
    count = 0
    block = text_item.document().begin()
    while block.isValid():
        block_layout = block.layout()
        origin = block_layout.position()
        for index in range(block_layout.lineCount()):
            for run in block_layout.lineAt(index).glyphRuns():
                raw_font = run.rawFont()
                for glyph, position in zip(run.glyphIndexes(), run.positions()):
                    glyph_path = raw_font.pathForGlyph(glyph)
                    glyph_path.translate(origin + position)
                    chunk.addPath(glyph_path)
                    count += 1
                    if count == HALO_CHUNK_GLYPHS:
                        chunks.append(chunk)
                        chunk = QtGui.QPainterPath()
                        count = 0
        block = block.next()
    if count:
        chunks.append(chunk)
    return chunks


def text_glyph_path(text_item):
    """ Outline of all the glyphs, as drawn by the text layout. """
    glyphs = QtGui.QPainterPath()
    for chunk in text_glyph_chunks(text_item):
        glyphs.addPath(chunk)
    return glyphs


def _halo_key(text_item, width):
    """ Everything that changes where the glyphs are drawn. """
    document = text_item.document()
    fmt = document.rootFrame().frameFormat()
    return (text_item.toPlainText(), text_item.font().toString(), text_item.textWidth(), width,
            fmt.leftMargin(), fmt.topMargin(), fmt.rightMargin(), int(document.defaultTextOption().alignment().value))


HALO_SHARED_PATHS = 2000
_halo_paths_shared = OrderedDict()


def text_halo_paths(text_item, width=HALO_WIDTH):
    """ (band around the glyph outline, glyphs, the same two in chunks), cached until the text, font or
    layout changes. """

    document = text_item.document()
    if document is None or document.isEmpty():
        return None
    key = _halo_key(text_item, width)
    cached = getattr(text_item, '_halo_cache', None)
    if cached is not None and cached[0] == key:
        return cached[1]
    # relation labels repeat the same few texts, so equal texts share one outline
    paths = _halo_paths_shared.get(key)
    if paths is None:
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(width)
        stroker.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        chunks = [(stroker.createStroke(chunk), chunk) for chunk in text_glyph_chunks(text_item)]
        glyphs = QtGui.QPainterPath()
        for _band_chunk, glyph_chunk in chunks:
            glyphs.addPath(glyph_chunk)
        # one stroke of the whole outline for PDF and SVG, where overlapping chunks could cancel out
        paths = (stroker.createStroke(glyphs), glyphs, chunks)
        _halo_paths_shared[key] = paths
        if len(_halo_paths_shared) > HALO_SHARED_PATHS:
            _halo_paths_shared.popitem(last=False)
    else:
        _halo_paths_shared.move_to_end(key)
    text_item._halo_cache = (key, paths)
    return paths


def text_halo_path(text_item, width=HALO_WIDTH):
    """ Band around the glyph outline. The text painted on top covers the inside of the glyphs. """
    paths = text_halo_paths(text_item, width)
    return paths[0] if paths else None


# PDF, SVG and recorded pictures keep the halo as a shape
VECTOR_PAINT_ENGINES = (QtGui.QPaintEngine.Type.Pdf, QtGui.QPaintEngine.Type.SVG,
                        QtGui.QPaintEngine.Type.Picture, QtGui.QPaintEngine.Type.MacPrinter)
HALO_IMAGE_MAX_SIDE = 4096
HALO_MIN_TEXT_PIXELS = 8  # smaller text cannot be read, so it gets no halo
HALO_IMAGE_BUDGET = 64 * 1024 * 1024  # bytes kept for halo images, oldest dropped first
_halo_images = OrderedDict()
_halo_images_bytes = 0


def _halo_image(text_item, width, color, pixel_scale, offset):
    """ Halo filled once into an image at the screen scale, starting offset pixels into it so it lands on the
    same fraction of a pixel as the text. Equal names and labels share it, and copying it is far cheaper than
    filling the outline shape on every repaint. Returns (image or None, item rect). """

    global _halo_images_bytes
    key = (_halo_key(text_item, width), round(pixel_scale, 3), color.rgb(), offset)
    cached = _halo_images.get(key)
    if cached is not None:
        _halo_images.move_to_end(key)
        return cached
    band, glyphs, chunks = text_halo_paths(text_item, width)
    bounds = band.boundingRect().united(glyphs.boundingRect()).adjusted(-1, -1, 1, 1)
    image_width = math.ceil(bounds.width() * pixel_scale) + 1
    image_height = math.ceil(bounds.height() * pixel_scale) + 1
    if max(image_width, image_height) > HALO_IMAGE_MAX_SIDE:
        return None, bounds
    image = QtGui.QImage(image_width, image_height, QtGui.QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.translate(offset[0], offset[1])
    painter.scale(pixel_scale, pixel_scale)
    painter.translate(-bounds.topLeft())
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    opaque = QtGui.QColor(color)
    opaque.setAlpha(255)
    painter.setBrush(QtGui.QBrush(opaque))
    # filled together in one opaque image, the pieces merge with no overlap in transparency
    for band_chunk, glyph_chunk in chunks:
        painter.drawPath(band_chunk)
        painter.drawPath(glyph_chunk)
    painter.end()
    result = (image, bounds)
    _halo_images[key] = result
    _halo_images_bytes += image.sizeInBytes()
    while _halo_images_bytes > HALO_IMAGE_BUDGET and len(_halo_images) > 1:
        _old_key, (old_image, _old_bounds) = _halo_images.popitem(last=False)
        _halo_images_bytes -= old_image.sizeInBytes()
    return result


def paint_text_halo(painter, text_item, color=HALO_COLOR, width=HALO_WIDTH):
    """ Light outline hugging the glyphs, so lines behind the text stay visible around it.
    Always drawn as a shape, never as text, so screen font smoothing adds no colored fringes. """

    document = text_item.document()
    if document is None or document.isEmpty():
        return
    engine = painter.paintEngine()
    vector = engine is not None and engine.type() in VECTOR_PAINT_ENGINES
    if not vector:
        device = painter.device()
        ratio = device.devicePixelRatioF() if device is not None else 1.0
        transform = painter.worldTransform()
        pixel_scale = math.sqrt(abs(transform.determinant())) * ratio
        if (pixel_scale * width < 1.0 or
                QtGui.QFontMetricsF(text_item.font()).height() * pixel_scale < HALO_MIN_TEXT_PIXELS):
            return  # text too small to read at this zoom, a halo would only cost time
    band, glyphs, chunks = text_halo_paths(text_item, width)
    painter.save()
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    if not vector:
        corner = band.boundingRect().united(glyphs.boundingRect()).adjusted(-1, -1, 1, 1).topLeft()
        corner = transform.map(corner) * ratio  # in screen pixels
        pixel_x, pixel_y = math.floor(corner.x()), math.floor(corner.y())
        # quarter pixel steps keep the halo on the text and few images per name
        offset = (round((corner.x() - pixel_x) * 4) / 4, round((corner.y() - pixel_y) * 4) / 4)
        image, _bounds = _halo_image(text_item, width, color, pixel_scale, offset)
        if image is not None:
            painter.resetTransform()
            painter.setOpacity(painter.opacity() * color.alphaF())
            painter.drawImage(QtCore.QRectF(pixel_x / ratio, pixel_y / ratio,
                                            image.width() / ratio, image.height() / ratio), image)
            painter.restore()
            return
    painter.setPen(QtCore.Qt.PenStyle.NoPen)
    painter.setBrush(QtGui.QBrush(color))
    if vector:
        painter.drawPath(band)
    else:
        for band_chunk, _glyph_chunk in chunks:  # too large for an image
            painter.drawPath(band_chunk)
    painter.restore()


def add_appearance_submenus(menu, nodes):
    """ Node shape, Node size and Hierarchy line width submenus for code and category nodes.
    Returns {action: kwargs for ViewGraph.apply_node_appearance}. """
    from .view_graph import LinkGraphicsItem

    actions = {}
    shape_menu = menu.addMenu(_("Node shape"))
    for shape in NODE_SHAPES:
        actions[shape_menu.addAction(node_shape_names()[shape])] = {'shape': shape}

    def add_mode_menu(title, key):
        mode_menu = menu.addMenu(title)
        actions[mode_menu.addAction(size_mode_names()["none"])] = {key: "none"}
        frequency_menu = mode_menu.addMenu(_("By frequency"))
        for mode in ("branch", "project"):
            actions[frequency_menu.addAction(size_mode_names()[mode])] = {key: mode}
        return mode_menu

    add_mode_menu(_("Node size"), 'size_mode')
    has_hierarchy_line = False
    scene = nodes[0].scene() if nodes else None
    if scene is not None:
        for line in scene.items():
            pair = hierarchy_parent_child(line) if isinstance(line, LinkGraphicsItem) else None
            if pair is not None and pair[1] in nodes:
                has_hierarchy_line = True
                break
    line_menu = add_mode_menu(_("Hierarchy line width"), 'line_mode')
    line_menu.setEnabled(has_hierarchy_line)
    return actions


def hierarchy_parent_child(line):
    """ (parent, child) when the link is a category / code / sub-code hierarchy line, else None. """
    from .view_graph import TextGraphicsItem, is_parent_child
    fw = getattr(line, 'from_widget', None)
    tw = getattr(line, 'to_widget', None)
    if not isinstance(fw, TextGraphicsItem) or not isinstance(tw, TextGraphicsItem):
        return None
    if getattr(line, 'label', '') or getattr(line, '_is_cooc_line', False):
        return None
    if line.line_type == QtCore.Qt.PenStyle.DotLine and line.color == "blue":
        return None
    if is_parent_child(fw, tw):
        return tw, fw
    if is_parent_child(tw, fw):
        return fw, tw
    return None


# --- code and category nodes: shape, layout and painting 2026-11-12 ---
class NodeShapeMixin:
    """ Shape, font and painting of code and category nodes. Mixed into TextGraphicsItem. """

    @property
    def node_shape(self):
        """ Shape name, or None while the node waits for the graph default. """
        return self._node_shape

    @node_shape.setter
    def node_shape(self, shape):
        self._node_shape = shape if shape in NODE_SHAPES else None
        # text color depends on the shape: on the code color or on a light halo
        self.setDefaultTextColor(QtGui.QColor(TextColor(self.code_or_cat['color']).recommendation))
        self._apply_shape_layout()

    @property
    def is_ellipse(self):
        """ Kept for the line geometry helpers. """
        return self._node_shape == "ellipse"

    @is_ellipse.setter
    def is_ellipse(self, value):
        if value:
            self.node_shape = "ellipse"
        elif self._node_shape == "ellipse":
            self.node_shape = "rectangle"

    def apply_font(self):
        """ Font from font_size and bold. """
        weight = QtGui.QFont.Weight.Bold if self.bold else QtGui.QFont.Weight.Normal
        self.setFont(QtGui.QFont(self.settings['font'], self.font_size, weight))

    def setDefaultTextColor(self, color):
        """ Icon and circle shapes draw the name on a light halo, so the text stays dark. """
        if getattr(self, '_node_shape', None) in ("icon", "circle"):
            color = QtGui.QColor(ON_CANVAS_TEXT_COLOR)
        super().setDefaultTextColor(color)

    def setFont(self, font):
        super().setFont(font)
        self._apply_shape_layout()

    def setPlainText(self, text):
        super().setPlainText(text)
        self._apply_shape_layout()

    def setTextWidth(self, width):
        super().setTextWidth(width)
        self._apply_shape_layout()

    def _shape_metrics(self):
        """ Sizes in pixels of the icon square and the circle diameter for the current font. """
        line_height = QtGui.QFontMetricsF(self.font()).height()
        return max(8.0, round(line_height * 0.8)), max(16.0, round(line_height * 1.8))

    def _apply_shape_layout(self):
        """ Reserve room for the icon (left) or the circle (top) through the document margins. """
        self._shape_geometry = {}  # circle and name areas are measured again on demand
        self._shape_version = getattr(self, '_shape_version', 0) + 1  # lines recompute their ends
        document = self.document()
        if document is None:
            return
        base = document.documentMargin()
        left = right = top = bottom = base
        alignment = QtCore.Qt.AlignmentFlag.AlignLeft
        icon_side, diameter = self._shape_metrics()
        if self._node_shape == "icon":
            if self.has_shape_icon():
                left = base + icon_side + 5
        elif self._node_shape == "ellipse":
            # keep the text inside the ellipse instead of touching its border
            line_height = QtGui.QFontMetricsF(self.font()).height()
            left = right = base + line_height * 0.6
            top = bottom = base + 1
        elif self._node_shape == "circle":
            top = base + diameter + 3
            alignment = QtCore.Qt.AlignmentFlag.AlignHCenter
            if self.textWidth() <= 0:
                metrics = QtGui.QFontMetricsF(self.font())
                text_w = max([metrics.horizontalAdvance(line) for line in self.toPlainText().split("\n")] or [0])
                extra = (diameter - text_w) / 2
                if extra > 0:
                    left = right = base + extra
        option = document.defaultTextOption()
        if option.alignment() != alignment:
            option.setAlignment(alignment)
            document.setDefaultTextOption(option)
        frame = document.rootFrame()
        fmt = frame.frameFormat()
        if (fmt.leftMargin(), fmt.rightMargin(), fmt.topMargin(), fmt.bottomMargin()) != (left, right, top, bottom):
            fmt.setLeftMargin(left)
            fmt.setRightMargin(right)
            fmt.setTopMargin(top)
            fmt.setBottomMargin(bottom)
            self.prepareGeometryChange()
            frame.setFrameFormat(fmt)
        self.update()

    def has_shape_icon(self):
        """ Only codes get the color square of the icon shape; a white square would look like a code. """
        return self.code_or_cat.get('cid') is not None

    def _cached_geometry(self, name, measure):
        """ Geometry kept until the shape layout runs again. Lines ask for it on every drag frame. """
        cache = getattr(self, '_shape_geometry', None)
        if cache is None:
            cache = self._shape_geometry = {}
        if name not in cache:
            cache[name] = measure()
        return QtCore.QRectF(cache[name])

    def circle_rect(self):
        """ Circle of the circle shape, in item coordinates. """
        return self._cached_geometry('circle', self._measure_circle_rect)

    def _measure_circle_rect(self):
        _icon, diameter = self._shape_metrics()
        br = self.boundingRect()
        top = self.document().documentMargin() if self.document() is not None else 4
        return QtCore.QRectF(br.center().x() - diameter / 2, top, diameter, diameter)

    def label_rect(self):
        """ Area the name text really takes, in item coordinates. """
        return self._cached_geometry('label', self._measure_label_rect)

    def _measure_label_rect(self):
        area = QtCore.QRectF()
        document = self.document()
        if document is None:
            return area
        block = document.begin()
        while block.isValid():
            layout = block.layout()
            origin = layout.position()
            for index in range(layout.lineCount()):
                area = area.united(layout.lineAt(index).naturalTextRect().translated(origin))
            block = block.next()
        return area

    def icon_rect(self):
        """ Color square of the icon shape, in item coordinates. """
        icon_side, _diameter = self._shape_metrics()
        margin = self.document().documentMargin() if self.document() is not None else 4
        first_line_h = QtGui.QFontMetricsF(self.font()).height()
        return QtCore.QRectF(margin, margin + (first_line_h - icon_side) / 2, icon_side, icon_side)

    def _take_graph_defaults(self):
        """ New nodes take the graph shape and size mode as soon as they enter the canvas,
        so layouts measure the final shape. """
        graph = getattr(self.scene(), 'parent', None) if self.scene() is not None else None
        default_shape = getattr(graph, 'graph_node_shape', None)
        if self._node_shape is None and default_shape in NODE_SHAPES:
            self.node_shape = default_shape
        if self.size_mode is None and getattr(graph, 'graph_size_mode', None) in SIZE_MODES:
            self.size_mode = graph.graph_size_mode

    def paint(self, painter, option, widget):
        painter.save()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        color = QtGui.QColor(self.code_or_cat.get('color') or "#FFFFFF")
        if not color.isValid():
            color = QtGui.QColor("#FFFFFF")
        # white categories need a visible outline on a light canvas
        outline = QtGui.QColor("#9E9E9E") if color.lightness() > 230 else color.darker(130)
        br = self.boundingRect()
        shape = self._node_shape or "rectangle"
        if shape in ("icon", "circle"):
            paint_text_halo(painter, self)
            painter.setPen(QtGui.QPen(outline, 1))
            painter.setBrush(QtGui.QBrush(color))
            if shape == "icon":
                if self.has_shape_icon():
                    painter.drawRoundedRect(self.icon_rect(), 2, 2)
            else:
                painter.drawEllipse(self.circle_rect())
        else:
            painter.setBrush(QtGui.QBrush(color, style=QtCore.Qt.BrushStyle.SolidPattern))
            if shape == "ellipse":
                # same soft outline as the circle shape
                painter.setPen(QtGui.QPen(outline, 1))
                painter.drawEllipse(br.adjusted(0.5, 0.5, -0.5, -0.5))
            else:
                painter.drawRoundedRect(br, NODE_CORNER_RADIUS, NODE_CORNER_RADIUS)
        painter.restore()
        super().paint(painter, option, widget)


# --- code colors, shared by the graph and the code organiser 2026-11-13 ---
class CodeColorMixin:
    """ Change the color of the selected codes. The host decides when the color reaches the project:
    the graph saves it at once, the code organiser keeps it until Apply. """

    def _color_code_nodes(self, nodes):
        """ Code nodes among nodes, skipping merged and deleted ones. """
        return [n for n in nodes if getattr(n, 'code_or_cat', None) is not None
                and n.code_or_cat.get('cid') is not None and n.code_or_cat.get('name', '') != ""
                and not n.code_or_cat.get('delete')]

    def _store_codes_color(self, cids, color):
        """ Keep the new color. Returns False when it could not be kept. """
        raise NotImplementedError

    def _after_codes_color(self, cids, color):
        """ Called once the nodes show the new color. """

    def change_codes_color(self, nodes):
        """ Change the color of the code nodes in nodes. Other nodes are skipped. F5 calls it too. """

        code_nodes = self._color_code_nodes(nodes)
        if not code_nodes:
            return
        cids = list(dict.fromkeys(n.code_or_cat['cid'] for n in code_nodes))
        current = {'name': code_nodes[0].code_or_cat['name'].strip(), 'color': code_nodes[0].code_or_cat['color']}
        if len(cids) > 1:
            current['name'] = _("Selected codes") + f" ({len(cids)})"
        ui = DialogColorSelect(self.app, current, self)
        if not ui.exec():
            return
        new_color = ui.get_color()
        if not new_color or not self._store_codes_color(cids, new_color):
            return
        for item in self._color_code_nodes(self.scene.items()):
            if item.code_or_cat['cid'] in cids:
                item.code_or_cat['color'] = new_color
                item.setDefaultTextColor(QtGui.QColor(TextColor(new_color).recommendation))
                item.update()
        self._after_codes_color(cids, new_color)
        self.scene.update()


# --- appearance of the whole graph 2026-11-12 ---
class GraphAppearanceMixin(CodeColorMixin):
    """ Appearance button, frequency sizes and code colors. Mixed into ViewGraph. """

    def _setup_appearance_button(self):
        """ Appearance button and the defaults it applies to new nodes. """

        self.ui.pushButton_appearance.setIcon(qta.icon('mdi6.palette-outline', options=[{'scale_factor': 1.4}]))
        self.ui.pushButton_appearance.pressed.connect(self.open_appearance_dialog)
        self.ui.pushButton_appearance.setToolTip(_("Appearance"))
        self.graph_node_shape = "rectangle"
        self.graph_size_mode = "none"
        self.graph_line_mode = "none"

    def apply_appearance_to_nodes(self, nodes, toggle_bold=False, font_size=None):
        """ Apply Bold / Font size to every text node in nodes,
        mirroring the per-item context menu behavior (item.bold + item.font_size
        + setFont). Bold on a mixed selection unifies: if any node is not bold,
        all become bold; if all are bold, all become normal. """
        from .view_graph import TextGraphicsItem

        text_nodes = [n for n in nodes if hasattr(n, 'setFont')
                      and (hasattr(n, 'bold') or hasattr(n, 'font_size'))]
        if not text_nodes:
            return
        self._save_undo_state()
        new_bold = None
        if toggle_bold:
            new_bold = any(not getattr(n, 'bold', False) for n in text_nodes)
        for node in text_nodes:
            if new_bold is not None and hasattr(node, 'bold'):
                node.bold = new_bold
            if font_size is not None and hasattr(node, 'font_size'):
                node.font_size = font_size
                if isinstance(node, TextGraphicsItem):
                    node.size_mode = "none"  # manual size stops the frequency sizing
            size = getattr(node, 'font_size', 9) or 9
            weight = QtGui.QFont.Weight.Bold if getattr(node, 'bold', False) \
                else QtGui.QFont.Weight.Normal
            try:
                node.setFont(QtGui.QFont(self.app.settings['font'], size, weight))
            except Exception:
                continue
        # bounding rects changed: redraw lines, labels, minimap
        self.finalize_graph_operation(fit_view=False)

    def open_appearance_dialog(self):
        """ Appearance button: shape, size and hierarchy line width for all codes and categories.
        The choice also becomes the default for codes and categories added later. """
        from .view_graph import TextGraphicsItem

        ui = DialogGraphAppearance(self.app, self.graph_node_shape, self.graph_size_mode,
                                   self.graph_line_mode, self)
        if not ui.exec():
            return
        self._save_undo_state()
        self.graph_node_shape = ui.selected_shape
        self.graph_size_mode = ui.selected_size_mode
        self.graph_line_mode = ui.selected_line_mode
        nodes = [i for i in self.scene.items() if isinstance(i, TextGraphicsItem)]
        self._set_nodes_appearance(nodes, ui.selected_shape, ui.selected_size_mode, ui.selected_line_mode)
        self._refresh_after_appearance_change()

    def apply_node_appearance(self, nodes, shape=None, size_mode=None, line_mode=None):
        """ Context menu entry point for one node or a multi-selection. """
        from .view_graph import TextGraphicsItem

        nodes = [n for n in nodes if isinstance(n, TextGraphicsItem)]
        if not nodes:
            return
        self._save_undo_state()
        self._set_nodes_appearance(nodes, shape, size_mode, line_mode)
        self._refresh_after_appearance_change()

    def _refresh_after_appearance_change(self):
        """ Sizes, line ends and minimap after a shape or size change. The full sync is not needed,
        nothing changed in the project, and it grows with the square of the nodes. """

        self.update_frequency_appearance(redraw_lines=False)
        self.redraw_lines_of_nodes()
        self._refresh_minimap()

    def _set_nodes_appearance(self, nodes, shape, size_mode, line_mode):
        """ Set the modes; leaving a frequency mode restores the default size or width.
        Sizes and widths by frequency are computed by update_frequency_appearance. """
        from .view_graph import LinkGraphicsItem

        for node in nodes:
            if shape is not None:
                node.node_shape = shape
            if size_mode is not None:
                if size_mode == "none" and node.size_mode in ("branch", "project"):
                    node.font_size = DEFAULT_NODE_FONT_SIZE
                    node.apply_font()
                node.size_mode = size_mode
        if line_mode is None:
            return
        for line in self.scene.items():
            if not isinstance(line, LinkGraphicsItem):
                continue
            pair = hierarchy_parent_child(line)
            if pair is None or pair[1] not in nodes:
                continue
            if line_mode == "none" and line.width_mode in ("branch", "project"):
                line.line_width = DEFAULT_LINE_WIDTH
            line.width_mode = line_mode
            line.redraw()

    def update_frequency_appearance(self, redraw_lines=True):
        """ Give new nodes and hierarchy lines the graph defaults, then size them by frequency.
        Run by the synchronizer, so sizes follow coding changes made in other dialogs. """
        from .view_graph import LinkGraphicsItem, TextGraphicsItem

        nodes = [i for i in self.scene.items() if isinstance(i, TextGraphicsItem)]
        lines = []
        for item in self.scene.items():
            if isinstance(item, LinkGraphicsItem):
                pair = hierarchy_parent_child(item)
                if pair is not None:
                    lines.append((item, pair[1]))
        for node in nodes:
            if node.node_shape is None:
                node.node_shape = self.graph_node_shape
            if node.size_mode is None:
                node.size_mode = self.graph_size_mode
        for line, _child in lines:
            if line.width_mode is None:
                line.width_mode = self.graph_line_mode
        sized_nodes = [n for n in nodes if n.size_mode in ("branch", "project")]
        sized_lines = [(line, child) for line, child in lines if line.width_mode in ("branch", "project")]
        if not sized_nodes and not sized_lines:
            return
        ratios = self._frequency_ratios(nodes)
        for node in sized_nodes:
            size = frequency_font_size(ratios[node][node.size_mode])
            if size != node.font_size:
                node.font_size = size
                node.apply_font()
        for line, child in sized_lines:
            line.line_width = frequency_line_width(ratios[child][line.width_mode])
        if redraw_lines:
            self.redraw_lines_of_nodes()

    def _coding_frequency_totals(self):
        """ Coding counts of all coders (text, image and A/V).
        Returns (own_total dict by cid, code_total(cid) with sub-codes, category_total(catid), project total). """

        cur = self.app.conn.cursor()
        own_total = {}
        for table in ("code_text", "code_image", "code_av"):
            cur.execute(f"select cid, count(*) from {table} group by cid")
            for cid_v, n in cur.fetchall():
                own_total[cid_v] = own_total.get(cid_v, 0) + n
        children_by_supercid = {}
        codes_by_catid = {}
        for code in self.codes:
            sup = code.get('supercid')
            if sup is not None:
                children_by_supercid.setdefault(sup, []).append(code['cid'])
            elif code.get('catid') is not None:
                codes_by_catid.setdefault(code['catid'], []).append(code['cid'])
        cat_children = {}
        for cat in self.categories:
            sup = cat.get('supercatid')
            if sup is not None:
                cat_children.setdefault(sup, []).append(cat['catid'])

        def code_total(cid_v, guard=0):
            """ Own codings plus all descendant sub-codes. """
            total = own_total.get(cid_v, 0)
            if guard > 50:
                return total
            for child in children_by_supercid.get(cid_v, []):
                total += code_total(child, guard + 1)
            return total

        def category_total(catid_v, guard=0):
            """ Aggregated totals of top codes across the category descendancy. """
            total = 0
            if guard > 50:
                return total
            for cid_v in codes_by_catid.get(catid_v, []):
                total += code_total(cid_v)
            for sub in cat_children.get(catid_v, []):
                total += category_total(sub, guard + 1)
            return total

        project_total = sum(own_total.get(code['cid'], 0) for code in self.codes)
        return own_total, code_total, category_total, project_total

    def _frequency_ratios(self, nodes):
        """ Share of each node in the total of its branch root in view (category or parent code)
        and in the project total. Nodes with no branch in view are measured against the largest root. """

        _own, code_total, category_total, project_total = self._coding_frequency_totals()
        totals = {}
        for n in nodes:
            if n.code_or_cat.get('cid') is not None:
                totals[n] = code_total(n.code_or_cat['cid'])
            else:
                totals[n] = category_total(n.code_or_cat.get('catid'))
        by_cid = {n.code_or_cat['cid']: n for n in nodes if n.code_or_cat.get('cid') is not None}
        by_catid = {n.code_or_cat.get('catid'): n for n in nodes if n.code_or_cat.get('cid') is None}

        def scene_parent(n):
            # same rule as the hierarchy lines: sub-codes hang only from their parent code
            info = n.code_or_cat
            if info.get('cid') is not None:
                if info.get('supercid') is not None:
                    return by_cid.get(info['supercid'])
                return by_catid.get(info.get('catid')) if info.get('catid') is not None else None
            return by_catid.get(info.get('supercatid')) if info.get('supercatid') is not None else None

        parents = {n: scene_parent(n) for n in nodes}
        with_children = {p for p in parents.values() if p is not None}

        def root_of(n):
            seen = {n}
            while parents.get(n) is not None and parents[n] not in seen:
                n = parents[n]
                seen.add(n)
            return n

        loose = {n for n in nodes if parents[n] is None and n not in with_children}
        loose_max = max([totals[n] for n in nodes if parents[n] is None] or [0])
        ratios = {}
        for n in nodes:
            reference = loose_max if n in loose else totals[root_of(n)]
            branch = totals[n] / reference if reference > 0 else 0.0
            project = totals[n] / project_total if project_total > 0 else 0.0
            ratios[n] = {'branch': min(1.0, branch), 'project': min(1.0, project)}
        return ratios

    def redraw_lines_of_nodes(self):
        """ Re-anchor all lines after node sizes changed. """
        from .view_graph import FreeLineGraphicsItem, LinkGraphicsItem

        for item in self.scene.items():
            if isinstance(item, (LinkGraphicsItem, FreeLineGraphicsItem)):
                try:
                    item.redraw()
                except RuntimeError:
                    continue
        self.scene.update()

    def _color_code_nodes(self, nodes):
        """ Code nodes among nodes; cases, files and other graph items have no code color. """
        from .view_graph import TextGraphicsItem

        return [n for n in nodes if isinstance(n, TextGraphicsItem) and n.code_or_cat.get('cid') is not None]

    def _store_codes_color(self, cids, color):
        """ The graph saves the color in the project at once. """

        cur = self.app.conn.cursor()
        try:
            for cid in cids:
                cur.execute("update code_name set color=? where cid=?", [color, cid])
            self.app.conn.commit()
        except sqlite3.Error as err:
            self.app.conn.rollback()
            logger.error(f"change_codes_color: {err}")
            Message(self.app, _("Error"), str(err), "warning").exec()
            return False
        self.app.delete_backup = False
        for code in self.codes:
            if code['cid'] in cids:
                code['color'] = color
        return True

    def _after_codes_color(self, cids, color):
        if getattr(self.app, 'project_events', None) is not None:
            self.app.project_events.emit_table_changes(["code_name"], source=self)

    def _load_graph_style(self, grid):
        """ Defaults for new nodes and lines; graphs saved before v18 keep the classic look. """
        from .view_graph import GRAPH_V18_COLUMNS, table_has_columns

        self.graph_node_shape, self.graph_size_mode, self.graph_line_mode = "rectangle", "none", "none"
        if not table_has_columns(self.app.conn, "graph", GRAPH_V18_COLUMNS["graph"]):
            return
        cur = self.app.conn.cursor()
        cur.execute("select node_shape, node_size_mode, line_width_mode from graph where grid=?", [grid])
        row = cur.fetchone()
        if row is None:
            return
        if row[0] in NODE_SHAPES:
            self.graph_node_shape = row[0]
        if row[1] in SIZE_MODES:
            self.graph_size_mode = row[1]
        if row[2] in SIZE_MODES:
            self.graph_line_mode = row[2]


# --- organization layouts, shared by the graph and the code organiser 2026-11-13 ---
class NodeLayoutMixin:
    """ Organization layouts shared by the graph and the code organiser. The host gives its nodes and lines
    in _organize_collect and can react before and after a layout change. """

    def _setup_organize_button(self, button, icon_scale=1.4):
        """ Magic wand button that opens the organization models. """
        button.setIcon(qta.icon('mdi6.auto-fix', options=[{'scale_factor': icon_scale}]))
        button.pressed.connect(self.open_organization_menu)

    def _organize_collect(self):
        """ (nodes, lines) to organize. Each host lists its own items. """
        raise NotImplementedError

    @staticmethod
    def _is_structural_link(link):
        """ Lines that shape the trees. In the code organiser every line is a hierarchy line. """
        return True

    def _before_layout_change(self):
        """ Called once before a layout chosen in the organization menu. """

    def _after_layout_change(self):
        """ Called after the nodes have been moved. """

    def open_organization_menu(self):
        """ Single dialog dispatching to the four organize_* layouts. """

        models = [
            {'name': _("Radial"), 'id': 'radial'},
            {'name': _("Top to Bottom"), 'id': 'hierarchical'},
            {'name': _("Left to Right"), 'id': 'lr'},
            {'name': _("Right to Left"), 'id': 'rl'},
        ]
        ui = DialogSelectItems(self.app, models, _("Select organization model"), "single")
        if not ui.exec():
            return
        selected = ui.get_selected()
        if not selected:
            return
        self._before_layout_change()
        dispatch = {
            'radial':       self.organize_radially,
            'hierarchical': self.organize_hierarchically,
            'lr':           lambda: self.organize_horizontal("LR"),
            'rl':           lambda: self.organize_horizontal("RL"),
        }
        fn = dispatch.get(selected['id'])
        if fn:
            fn()

    def node_organize_rank(self, n):
        """ Priority for root selection and sibling ordering in the layouts.
        Order: supercategories (2, top-level categories) < categories (3) < codes (4) < sub-codes (5)
        < everything else (6). The graph puts cases (0) and files (1) first. """

        code_or_cat = getattr(n, 'code_or_cat', None)
        if code_or_cat is not None:
            if code_or_cat.get('cid') is None:
                # category: top-level (no supercatid) outranks nested
                return 2 if code_or_cat.get('supercatid') is None else 3
            # code: plain code outranks sub-code (supercid)
            return 5 if code_or_cat.get('supercid') is not None else 4
        return 6

    def organize_sort_key(self, n, adjacency):
        """ Deterministic sort key for the organization layouts.
        Priority rank first, then most connected, then alphabetical. """

        return (self.node_organize_rank(n),
                -len(adjacency.get(n, ())),
                str(getattr(n, 'text', '')))

    def _organize_forest(self):
        """ Spanning forest shared by the layouts.
        1. One tree per structural component (hierarchy or case/file lines), so unrelated
           branches never merge and a relation line cannot hang one branch under another.
        2. Loose nodes linked by other lines (segments, memos, free text) join the nearest tree.
        3. Whatever is left forms its own trees over any line.
        Returns (nodes, links, roots, children). """

        nodes, links = self._organize_collect()
        node_set = set(nodes)
        adjacency = {n: set() for n in nodes}
        structural = {n: set() for n in nodes}
        for link in links:
            if not link.isVisible():
                continue
            u = getattr(link, 'from_widget', None)
            v = getattr(link, 'to_widget', None)
            if u is v or u not in node_set or v not in node_set:
                continue
            adjacency[u].add(v)
            adjacency[v].add(u)
            if self._is_structural_link(link):
                structural[u].add(v)
                structural[v].add(u)

        def key(n):
            return self.organize_sort_key(n, adjacency)

        ordered = sorted(nodes, key=key)
        children = {n: [] for n in nodes}
        claimed = set()
        roots = []

        def grow(root, graph):
            claimed.add(root)
            order = [root]
            i = 0
            while i < len(order):
                curr = order[i]
                i += 1
                for nb in sorted(graph[curr], key=key):
                    if nb not in claimed:
                        claimed.add(nb)
                        children[curr].append(nb)
                        order.append(nb)
            return order

        # first unclaimed node in priority order is always the best root of its component
        tree_nodes = []
        for n in ordered:
            if structural[n] and n not in claimed:
                roots.append(n)
                tree_nodes.extend(grow(n, structural))

        queue = list(tree_nodes)
        i = 0
        while i < len(queue):
            curr = queue[i]
            i += 1
            for nb in sorted(adjacency[curr], key=key):
                if nb not in claimed:
                    claimed.add(nb)
                    children[curr].append(nb)
                    queue.append(nb)

        for n in ordered:
            if n not in claimed:
                roots.append(n)
                grow(n, adjacency)
        return nodes, links, roots, children

    @staticmethod
    def _node_size(n):
        if hasattr(n, 'boundingRect'):
            r = n.boundingRect()
            return r.width(), r.height()
        return 100, 30

    @staticmethod
    def _shelf_offsets(sizes, axis, limit, gap):
        """ Offsets that place boxes in rows (axis 'x') or columns (axis 'y'), wrapping at limit. """

        offsets = []
        main_pos = 0
        cross_pos = 0
        line_thickness = 0
        for w, h in sizes:
            main, cross = (w, h) if axis == 'x' else (h, w)
            if main_pos > 0 and main_pos + main > limit:
                cross_pos += line_thickness + gap
                main_pos = 0
                line_thickness = 0
            offsets.append((main_pos, cross_pos) if axis == 'x' else (cross_pos, main_pos))
            main_pos += main + gap
            line_thickness = max(line_thickness, cross)
        return offsets

    def _best_shelf_offsets(self, sizes, axis, gap, aspect=1.5):
        """ Shelf offsets with the wrap limit that best fills a landscape view. """

        mains = [w if axis == 'x' else h for w, h in sizes]
        best = None
        run = -gap
        for m in mains:
            run += m + gap
            offsets = self._shelf_offsets(sizes, axis, run + 1, gap)
            width = max(ox + w for (ox, _oy), (w, _h) in zip(offsets, sizes))
            height = max(oy + h for (_ox, oy), (_w, h) in zip(offsets, sizes))
            score = max(width / aspect, height)
            if best is None or score < best[0]:
                best = (score, offsets)
        return best[1]

    def _normalize_block(self, pos):
        """ Shift block positions so its bounding box starts at 0,0. Returns (pos, width, height). """

        min_x = min(x for x, _y in pos.values())
        min_y = min(y for _x, y in pos.values())
        max_x = max(x + self._node_size(n)[0] for n, (x, _y) in pos.items())
        max_y = max(y + self._node_size(n)[1] for n, (_x, y) in pos.items())
        shifted = {n: (x - min_x, y - min_y) for n, (x, y) in pos.items()}
        return shifted, max_x - min_x, max_y - min_y

    def _organize_apply(self, blocks, links, axis, mirror=False):
        """ Pack the per-tree blocks, move the nodes and refresh.
        Trees with lines go first in priority order; loose nodes are gathered in a compact grid. """

        GAP = 80
        LOOSE_GAP = 30
        anchor = self.scene.itemsBoundingRect().topLeft()
        trees = []
        loose = []
        for pos in blocks:
            if len(pos) == 1:
                loose.append(next(iter(pos)))
            else:
                trees.append(self._normalize_block(pos))
        if loose:
            sizes = [self._node_size(n) for n in loose]
            offsets = self._best_shelf_offsets(sizes, 'x', LOOSE_GAP)
            trees.append(self._normalize_block({n: offsets[i] for i, n in enumerate(loose)}))

        sizes = [(w, h) for _pos, w, h in trees]
        offsets = self._best_shelf_offsets(sizes, axis, GAP)
        total_w = max(ox + w for (ox, _oy), (w, _h) in zip(offsets, sizes))

        for (pos, w, _h), (ox, oy) in zip(trees, offsets):
            if mirror:
                ox = total_w - ox - w
            for n, (x, y) in pos.items():
                nx = anchor.x() + ox + x
                ny = anchor.y() + oy + y
                if getattr(n, 'code_or_cat', None) is not None:
                    n.code_or_cat['x'] = nx
                    n.code_or_cat['y'] = ny
                n.setPos(nx, ny)
        for link in links:
            if hasattr(link, 'redraw'):
                link.redraw()
        self._after_layout_change()

    def _layout_tree_top_down(self, root, children):
        """ Top-left positions for one tree: parents centered over their children. """

        H_PAD = 30
        V_PAD = 40
        level_height = {}
        subtree_width = {}

        def measure(node, depth):
            w, h = self._node_size(node)
            level_height[depth] = max(level_height.get(depth, 0), h)
            kids = children.get(node, [])
            if not kids:
                subtree_width[node] = w
                return w
            total = sum(measure(c, depth + 1) for c in kids) + H_PAD * (len(kids) - 1)
            subtree_width[node] = max(w, total)
            return subtree_width[node]

        measure(root, 0)
        level_y = {}
        y = 0
        for d in range(max(level_height) + 1):
            level_y[d] = y
            y += level_height.get(d, 30) + V_PAD
        pos = {}

        def place(node, left_x, depth):
            kids = children.get(node, [])
            w = self._node_size(node)[0]
            if not kids:
                pos[node] = (left_x + (subtree_width[node] - w) / 2, level_y[depth])
                return left_x + subtree_width[node] / 2
            kids_width = sum(subtree_width[c] for c in kids) + H_PAD * (len(kids) - 1)
            child_left = left_x + (subtree_width[node] - kids_width) / 2
            centers = []
            for c in kids:
                centers.append(place(c, child_left, depth + 1))
                child_left += subtree_width[c] + H_PAD
            center = sum(centers) / len(centers)
            pos[node] = (center - w / 2, level_y[depth])
            return center

        place(root, 0, 0)
        return pos

    def _layout_tree_horizontal(self, root, children, direction):
        """ Top-left positions for one tree in columns, LR or RL; columns sized to their widest node. """

        H_GAP = 80
        V_GAP = 20
        level_width = {}

        def measure(node, depth):
            level_width[depth] = max(level_width.get(depth, 0), self._node_size(node)[0])
            for c in children.get(node, []):
                measure(c, depth + 1)

        measure(root, 0)
        level_x = {}
        x = 0
        for d in range(max(level_width) + 1):
            level_x[d] = x
            x += level_width.get(d, 100) + H_GAP
        pos = {}
        current_y = 0

        def place(node, depth):
            nonlocal current_y
            w, h = self._node_size(node)
            node_x = level_x[depth] if direction == "LR" else -level_x[depth] - w
            kids = children.get(node, [])
            if not kids:
                pos[node] = (node_x, current_y)
                y = current_y
                current_y += h + V_GAP
                return y
            ys = [place(c, depth + 1) for c in kids]
            parent_y = sum(ys) / len(ys)
            pos[node] = (node_x, parent_y)
            current_y = max(current_y, parent_y + h + V_GAP)
            return parent_y

        place(root, 0)
        return pos

    def _layout_tree_radial(self, root, children):
        """ Top-left positions for one tree as a star; ring spacing grows when the rim gets crowded. """

        leaves = {}
        depth_of = {}

        def count(node, depth):
            depth_of[node] = depth
            kids = children.get(node, [])
            leaves[node] = sum(count(c, depth + 1) for c in kids) if kids else 1
            return leaves[node]

        count(root, 0)
        max_depth = max(depth_of.values())
        rim = sum(self._node_size(n)[0] + 20 for n in depth_of if not children.get(n))
        radius_step = 280
        if max_depth > 0:
            radius_step = max(radius_step, rim / (2 * math.pi * max_depth))
        pos = {}

        def place(node, depth, a0, a1):
            w, h = self._node_size(node)
            if depth == 0:
                cx, cy = 0, 0
            else:
                r = max(200, depth * radius_step)
                mid = (a0 + a1) / 2
                cx, cy = r * math.cos(mid), r * math.sin(mid)
            pos[node] = (cx - w / 2, cy - h / 2)
            kids = children.get(node, [])
            if kids:
                per_leaf = (a1 - a0) / leaves[node]
                a = a0
                for c in kids:
                    span = leaves[c] * per_leaf
                    place(c, depth + 1, a, a + span)
                    a += span

        place(root, 0, 0, 2 * math.pi)
        return pos

    def organize_hierarchically(self):
        """ Top-down tree layout, one tree per branch placed side by side. """

        nodes, links, roots, children = self._organize_forest()
        if not nodes:
            return
        blocks = [self._layout_tree_top_down(r, children) for r in roots]
        self._organize_apply(blocks, links, 'x')

    def organize_horizontal(self, direction="LR"):
        """ Horizontal tree layout, LR (left to right) or RL (right to left), one tree per branch stacked. """

        nodes, links, roots, children = self._organize_forest()
        if not nodes:
            return
        blocks = [self._layout_tree_horizontal(r, children, direction) for r in roots]
        self._organize_apply(blocks, links, 'y', mirror=(direction == "RL"))

    def organize_radially(self):
        """ Radial layout, one star per branch arranged in a grid. """

        nodes, links, roots, children = self._organize_forest()
        if not nodes:
            return
        blocks = [self._layout_tree_radial(r, children) for r in roots]
        self._organize_apply(blocks, links, 'x')


# --- organizing, aligning and scaling the graph 2026-11-12 ---
class GraphLayoutMixin(NodeLayoutMixin):
    """ Graph side of the layouts: cases and files, relation lines, undo, and the align, distribute and
    scale buttons. Mixed into ViewGraph. """

    def _setup_layout_buttons(self):
        """ Organize, align, distribute, expand and compact buttons of the graph. """

        self._setup_organize_button(self.ui.pushButton_org_graph)
        buttons = ((self.ui.pushButton_align_vertical, 'mdi6.align-vertical-center',
                    lambda: self.align_selected("vertical")),
                   (self.ui.pushButton_align_horizontal, 'mdi6.align-horizontal-center',
                    lambda: self.align_selected("horizontal")),
                   (self.ui.pushButton_distribute_vertical, 'mdi6.distribute-vertical-center',
                    lambda: self.distribute_selected("vertical")),
                   (self.ui.pushButton_distribute_horizontal, 'mdi6.distribute-horizontal-center',
                    lambda: self.distribute_selected("horizontal")),
                   (self.ui.pushButton_expand_graph, 'mdi6.arrow-expand-all', lambda: self._scale_graph(1.10)),
                   (self.ui.pushButton_compact_graph, 'mdi6.arrow-collapse-all', lambda: self._scale_graph(0.90)))
        for button, icon, action in buttons:
            button.setIcon(qta.icon(icon, options=[{'scale_factor': 1.4}]))
            button.pressed.connect(action)

    def _before_layout_change(self):
        self._save_undo_state()

    def _after_layout_change(self):
        self.finalize_graph_operation()

    def node_organize_rank(self, n):
        """ Cases (0) and files (1) first, then the shared order of categories and codes. """
        from .view_graph import CaseTextGraphicsItem, FileTextGraphicsItem, TextGraphicsItem

        if isinstance(n, CaseTextGraphicsItem):
            return 0
        if isinstance(n, FileTextGraphicsItem):
            return 1
        if isinstance(n, TextGraphicsItem) and n.code_or_cat is not None:
            return super().node_organize_rank(n)
        return 6

    def _organize_collect(self):
        """ Visible nodes plus all lines considered by the organization layouts. """
        from .view_graph import (AVGraphicsItem, CaseTextGraphicsItem, FileTextGraphicsItem, FreeLineGraphicsItem,
                                 FreeTextGraphicsItem, LinkGraphicsItem, MemoGraphicsItem, PixmapGraphicsItem,
                                 TextGraphicsItem)

        node_types = (TextGraphicsItem, FreeTextGraphicsItem, CaseTextGraphicsItem,
                      FileTextGraphicsItem, PixmapGraphicsItem, AVGraphicsItem, MemoGraphicsItem)
        nodes = []
        links = []
        for item in self.scene.items():
            if isinstance(item, (LinkGraphicsItem, FreeLineGraphicsItem)):
                links.append(item)
            elif isinstance(item, node_types) and item.isVisible():
                nodes.append(item)
        return nodes, links

    @staticmethod
    def _is_structural_link(link):
        """ Hierarchy and case/file membership lines shape the trees; relations and co-occurrences do not. """
        from .view_graph import (CaseTextGraphicsItem, FileTextGraphicsItem, LinkGraphicsItem, TextGraphicsItem,
                                 is_parent_child)

        if isinstance(link, LinkGraphicsItem):
            # co-occurrence links lose their flag on reload, so judge by the codes themselves
            a, b = link.from_widget, link.to_widget
            if getattr(link, '_is_cooc_line', False) or not isinstance(a, TextGraphicsItem) \
                    or not isinstance(b, TextGraphicsItem):
                return False
            return is_parent_child(a, b) or is_parent_child(b, a)
        member_types = (CaseTextGraphicsItem, FileTextGraphicsItem)
        return isinstance(link.from_widget, member_types) or isinstance(link.to_widget, member_types)

    def align_selected(self, direction="vertical"):
        """ Align selected nodes to a vertical column or horizontal row.
        Uses Qt's BVH via selectedItems for O(K) lookup; clamps against collisions. """
        from .view_graph import (AVGraphicsItem, CaseTextGraphicsItem, FileTextGraphicsItem, FreeLineGraphicsItem,
                                 FreeTextGraphicsItem, LinkGraphicsItem, MemoGraphicsItem, PixmapGraphicsItem,
                                 TextGraphicsItem)
        valid_classes = (TextGraphicsItem, FreeTextGraphicsItem, CaseTextGraphicsItem,
                         FileTextGraphicsItem, PixmapGraphicsItem, AVGraphicsItem, MemoGraphicsItem)
        selected = [it for it in self.scene.selectedItems() if isinstance(it, valid_classes)]
        if len(selected) < 2:
            return
        self._save_undo_state()
        is_vertical = (direction == "vertical")
        centers = [it.sceneBoundingRect().center().y() if is_vertical else it.sceneBoundingRect().center().x()
                   for it in selected]
        target_center = sum(centers) / len(selected)
        selected.sort(key=lambda it: it.scenePos().x() if is_vertical else it.scenePos().y())
        padding = 15 if is_vertical else 10
        last_edge = float('-inf')
        for it in selected:
            rect = it.boundingRect()
            pos = it.pos()
            if is_vertical:
                new_y = target_center - (rect.height() / 2.0)
                new_x = max(pos.x(), last_edge + padding)
                it.setPos(new_x, new_y)
                last_edge = new_x + rect.width()
            else:
                new_x = target_center - (rect.width() / 2.0)
                new_y = max(pos.y(), last_edge + padding)
                it.setPos(new_x, new_y)
                last_edge = new_y + rect.height()
            if getattr(it, 'code_or_cat', None) is not None:
                it.code_or_cat['x'], it.code_or_cat['y'] = it.pos().x(), it.pos().y()
        for item in self.scene.items():
            if isinstance(item, (LinkGraphicsItem, FreeLineGraphicsItem)):
                item.redraw()
        self.scene.update()
        self._refresh_minimap()

    def distribute_selected(self, direction="vertical"):
        """ Distribute selected nodes uniformly along an axis. """
        from .view_graph import (AVGraphicsItem, CaseTextGraphicsItem, FileTextGraphicsItem, FreeLineGraphicsItem,
                                 FreeTextGraphicsItem, LinkGraphicsItem, MemoGraphicsItem, PixmapGraphicsItem,
                                 TextGraphicsItem)
        valid_classes = (TextGraphicsItem, FreeTextGraphicsItem, CaseTextGraphicsItem,
                         FileTextGraphicsItem, PixmapGraphicsItem, AVGraphicsItem, MemoGraphicsItem)
        selected = [it for it in self.scene.selectedItems() if isinstance(it, valid_classes)]
        if len(selected) < 3:
            return
        self._save_undo_state()
        is_vertical = (direction == "vertical")
        selected.sort(key=lambda it: it.sceneBoundingRect().center().y() if is_vertical else it.sceneBoundingRect().center().x())
        if is_vertical:
            total_size = sum(it.boundingRect().height() for it in selected)
            start_pos = selected[0].sceneBoundingRect().top()
            end_pos = selected[-1].sceneBoundingRect().bottom()
        else:
            total_size = sum(it.boundingRect().width() for it in selected)
            start_pos = selected[0].sceneBoundingRect().left()
            end_pos = selected[-1].sceneBoundingRect().right()
        total_span = end_pos - start_pos
        gap = (total_span - total_size) / float(len(selected) - 1)
        min_gap = 15.0
        if gap < min_gap:
            gap = min_gap
        current_pos = start_pos
        for it in selected:
            rect = it.boundingRect()
            if is_vertical:
                it.setPos(it.pos().x(), current_pos)
                current_pos += rect.height() + gap
            else:
                it.setPos(current_pos, it.pos().y())
                current_pos += rect.width() + gap
            if getattr(it, 'code_or_cat', None) is not None:
                it.code_or_cat['x'], it.code_or_cat['y'] = it.pos().x(), it.pos().y()
        for item in self.scene.items():
            if isinstance(item, (LinkGraphicsItem, FreeLineGraphicsItem)):
                item.redraw()
        self.scene.update()
        self._refresh_minimap()

    def _scale_graph(self, factor):
        """ Scale all node positions by `factor` relative to center of mass. """
        from .view_graph import (AVGraphicsItem, CaseTextGraphicsItem, FileTextGraphicsItem, FreeLineGraphicsItem,
                                 FreeTextGraphicsItem, LinkGraphicsItem, MemoGraphicsItem, PixmapGraphicsItem,
                                 TextGraphicsItem)
        nodes = [it for it in self.scene.items()
                 if isinstance(it, (TextGraphicsItem, FreeTextGraphicsItem, CaseTextGraphicsItem,
                                    FileTextGraphicsItem, PixmapGraphicsItem, AVGraphicsItem, MemoGraphicsItem))]
        if not nodes:
            return
        self._save_undo_state()
        cx = sum(it.pos().x() for it in nodes) / len(nodes)
        cy = sum(it.pos().y() for it in nodes) / len(nodes)
        for it in nodes:
            dx = it.pos().x() - cx
            dy = it.pos().y() - cy
            new_x = cx + dx * factor
            new_y = cy + dy * factor
            it.setPos(new_x, new_y)
            if hasattr(it, 'code_or_cat') and it.code_or_cat is not None:
                it.code_or_cat['x'] = new_x
                it.code_or_cat['y'] = new_y
        for item in self.scene.items():
            if isinstance(item, (LinkGraphicsItem, FreeLineGraphicsItem)):
                item.redraw()
        if factor > 1.0:
            rect = self.scene.itemsBoundingRect()
            rect.adjust(-100, -100, 100, 100)
            candidate = self.scene.sceneRect().united(rect)
            MAX_SCENE = 50000
            if candidate.width() > MAX_SCENE or candidate.height() > MAX_SCENE:
                candidate.setWidth(min(candidate.width(), MAX_SCENE))
                candidate.setHeight(min(candidate.height(), MAX_SCENE))
            self.scene.setSceneRect(candidate)
        self.scene.update()
        self._refresh_minimap()


# --- appearance window and previews 2026-11-12 ---
def render_scene_to_pixmap(scene, size, max_scale=1.0):
    """ Fit the items of scene into a transparent pixmap of the given size. """

    rect = scene.itemsBoundingRect().adjusted(-4, -4, 4, 4)
    pixmap = QtGui.QPixmap(size)
    pixmap.fill(QtCore.Qt.GlobalColor.transparent)
    if rect.isEmpty():
        return pixmap
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing)
    scale = min(max_scale, size.width() / rect.width(), size.height() / rect.height())
    target_w = rect.width() * scale
    target_h = rect.height() * scale
    target = QtCore.QRectF((size.width() - target_w) / 2, (size.height() - target_h) / 2, target_w, target_h)
    scene.render(painter, target, rect)
    painter.end()
    return pixmap


def sample_node(app, name, color, shape, font_size=10, bold=False, category=False):
    """ Code or category node not tied to the project, for previews. """
    from .view_graph import TextGraphicsItem

    sample = {'name': name, 'cid': None if category else -1, 'catid': -1 if category else None,
              'supercatid': None, 'supercid': None, 'x': 0, 'y': 0, 'color': color}
    return TextGraphicsItem(app, sample, font_size, bold, True, "", shape=shape)


def render_node_preview(app, shape, color="#F5A9A9", text=None, font_size=10, size=QtCore.QSize(150, 54)):
    """ Picture of a code node in the given shape. """

    scene = QtWidgets.QGraphicsScene()
    scene.addItem(sample_node(app, text or _("Code"), color, shape, font_size))
    return render_scene_to_pixmap(scene, size)


def render_appearance_preview(app, shape, size_mode, line_mode, size=QtCore.QSize(270, 200)):
    """ A category with three codes drawn with the chosen shape, sizes and line widths. """
    from .view_graph import LinkGraphicsItem

    samples = [(_("Code") + " 1", "#F5A9A9", 10), (_("Code") + " 2", "#81BEF7", 6),
               (_("Code") + " 3", "#BEF781", 2)]
    category_total = sum(count for _name, _color, count in samples)
    project_total = 40

    def ratio(count, mode):
        return count / (category_total if mode == "branch" else project_total)

    def font_for(count):
        return frequency_font_size(ratio(count, size_mode)) if size_mode in ("branch", "project") \
            else DEFAULT_NODE_FONT_SIZE

    scene = QtWidgets.QGraphicsScene()
    category = sample_node(app, _("Category"), "#FFFFFF", shape, font_for(category_total), True, True)
    scene.addItem(category)
    codes = []
    for name, color, count in samples:
        node = sample_node(app, name, color, shape, font_for(count))
        scene.addItem(node)
        codes.append((node, count))
    gap_x, gap_y = 14, 46
    row_width = sum(node.boundingRect().width() for node, _count in codes) + gap_x * (len(codes) - 1)
    category.setPos((row_width - category.boundingRect().width()) / 2, 0)
    x = 0
    row_top = category.boundingRect().height() + gap_y
    for node, _count in codes:
        node.setPos(x, row_top)
        x += node.boundingRect().width() + gap_x
    for node, count in codes:
        width = frequency_line_width(ratio(count, line_mode)) if line_mode in ("branch", "project") \
            else DEFAULT_LINE_WIDTH
        scene.addItem(LinkGraphicsItem(node, category, width, "solid", "gray"))
    return render_scene_to_pixmap(scene, size, max_scale=1.2)


class DialogGraphAppearance(QDialog):
    """ Appearance button of the graph: node shape cards, node size and hierarchy line width
    (no adjustment, or by frequency relative to the category / parent code total or the project total),
    with a live preview. """

    SHAPE_ICON_SIZE = QtCore.QSize(110, 52)

    def __init__(self, app, shape="rectangle", size_mode="none", line_mode="none", parent=None):
        super().__init__(parent)
        self.app = app
        self.ui = Ui_Dialog_graph_appearance()
        self.ui.setupUi(self)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        font = f"font: {self.app.settings['fontsize']}pt "
        font += f'"{self.app.settings["font"]}";'
        self.setStyleSheet(font)
        for title in (self.ui.label_shape_title, self.ui.label_size_title, self.ui.label_line_title,
                      self.ui.label_preview_title):
            title.setStyleSheet("font-weight: bold;")
        # shape cards follow the palette, so they suit the light and dark themes
        self.ui.widget_shapes.setStyleSheet(
            "QToolButton {border: 1px solid palette(mid); border-radius: 6px; padding: 6px;"
            " background: palette(base);}"
            "QToolButton:hover {border-color: palette(highlight);}"
            "QToolButton:checked {border: 2px solid palette(highlight); padding: 5px;}")
        self.ui.label_preview.setStyleSheet(
            "QLabel {border: 1px solid palette(mid); border-radius: 6px; background: palette(base);}")
        self._shape_buttons = {"rectangle": self.ui.toolButton_shape_rectangle,
                               "icon": self.ui.toolButton_shape_icon,
                               "ellipse": self.ui.toolButton_shape_ellipse,
                               "circle": self.ui.toolButton_shape_circle}
        for key, button in self._shape_buttons.items():
            button.setIcon(QtGui.QIcon(render_node_preview(app, key, size=self.SHAPE_ICON_SIZE)))
            button.setIconSize(self.SHAPE_ICON_SIZE)
            button.setText(node_shape_names()[key])
            button.toggled.connect(self._update_preview)
        self._shape_buttons.get(shape, self.ui.toolButton_shape_rectangle).setChecked(True)
        for combo in (self.ui.comboBox_size_reference, self.ui.comboBox_line_reference):
            for mode in ("branch", "project"):
                combo.addItem(size_mode_names()[mode], mode)
            combo.currentIndexChanged.connect(self._update_preview)
        self.ui.comboBox_size_reference.setToolTip(
            _("Category total, or the parent code when the branch in view has no category"))
        self.ui.comboBox_line_reference.setToolTip(self.ui.comboBox_size_reference.toolTip())
        self._set_mode(size_mode, self.ui.radioButton_size_none, self.ui.radioButton_size_frequency,
                       self.ui.comboBox_size_reference, self.ui.widget_size_reference)
        self._set_mode(line_mode, self.ui.radioButton_line_none, self.ui.radioButton_line_frequency,
                       self.ui.comboBox_line_reference, self.ui.widget_line_reference)
        self.ui.radioButton_size_frequency.toggled.connect(self.ui.widget_size_reference.setEnabled)
        self.ui.radioButton_line_frequency.toggled.connect(self.ui.widget_line_reference.setEnabled)
        for radio in (self.ui.radioButton_size_frequency, self.ui.radioButton_line_frequency):
            radio.toggled.connect(self._update_preview)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)
        self.selected_shape = shape
        self.selected_size_mode = size_mode
        self.selected_line_mode = line_mode
        self._update_preview()

    @staticmethod
    def _set_mode(mode, none_button, frequency_button, combo, reference_widget):
        frequency = mode in ("branch", "project")
        (frequency_button if frequency else none_button).setChecked(True)
        combo.setCurrentIndex(combo.findData("project" if mode == "project" else "branch"))
        reference_widget.setEnabled(frequency)

    @staticmethod
    def _get_mode(frequency_button, combo):
        if not frequency_button.isChecked():
            return "none"
        return combo.currentData() or "branch"

    def _current_choice(self):
        shape = next((key for key, button in self._shape_buttons.items() if button.isChecked()), "rectangle")
        return (shape,
                self._get_mode(self.ui.radioButton_size_frequency, self.ui.comboBox_size_reference),
                self._get_mode(self.ui.radioButton_line_frequency, self.ui.comboBox_line_reference))

    def _update_preview(self, *_args):
        shape, size_mode, line_mode = self._current_choice()
        size = self.ui.label_preview.size()
        if size.width() < 50 or size.height() < 50:
            size = self.ui.label_preview.minimumSize()
        self.ui.label_preview.setPixmap(
            render_appearance_preview(self.app, shape, size_mode, line_mode, size - QtCore.QSize(16, 16)))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_preview()

    def accept(self):
        self.selected_shape, self.selected_size_mode, self.selected_line_mode = self._current_choice()
        super().accept()
