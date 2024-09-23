# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

logging.debug("Loading ui.py")

# Import PyQt5 classes
import csv
import os

import numpy as np
from pyqtconfig import ConfigManager

from . import utils
from .globals import METABOHUNTER_HMDB_NAME_MAP, STATUS_QCOLORS, custom_pyqtconfig_hooks
from .qt import *

# import metabohunter
# Translation (@default context)
from .translate import tr

try:
    unicode
except:
    unicode = str


class ConfigPanel(QWidget):
    def __init__(self, parent, *args, **kwargs):
        super(ConfigPanel, self).__init__(parent.parent(), *args, **kwargs)

        self.config = parent.config
        self.tool = parent
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(10, 0, 10, 0)

    def finalise(self):
        self.layout.addStretch()
        self.setLayout(self.layout)

    def setListControl(self, control, list, checked):
        # Automatically set List control checked based on current options list
        items = control.GetItems()
        try:
            idxs = [items.index(e) for e in list]
            for idx in idxs:
                if checked:
                    control.Select(idx)
                else:
                    control.Deselect(idx)
        except:
            pass

    def addBottomSpacer(self, gd):
        gd.addItem(
            QSpacerItem(1, 100, QSizePolicy.Minimum, QSizePolicy.Minimum),
            gd.rowCount(),
            0,
        )


class SpectraList(QListWidget):
    pass


class QColorButton(QPushButton):
    """
    Custom Qt Widget to show a chosen color.

    Left-clicking the button shows the color-chooser, while
    right-clicking resets the color to None (no-color).
    """

    colorChanged = pyqtSignal()

    def __init__(self, is_reset_enabled=True, *args, **kwargs):
        super(QColorButton, self).__init__(*args, **kwargs)

        self._color = None
        self.setMaximumWidth(32)
        self.pressed.connect(self.onColorPicker)

        self.is_reset_enabled = is_reset_enabled

    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit()

        if self._color:
            self.setStyleSheet("background-color: %s;" % self._color)
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def onColorPicker(self):
        """
        Show color-picker dialog to select color.

        This should use the Qt-defined non-native dialog so custom colours
        can be auto-defined from the currently set palette - but it doesn't work due
        to a known bug - should auto-fix on Qt 5.2.2.
        """
        dlg = QColorDialog(self)
        if self._color:
            dlg.setCurrentColor(QColor(self._color))

        dlg.setOption(QColorDialog.DontUseNativeDialog)
        # FIXME: Add colors from current default set to the custom color table
        # dlg.setCustomColor(0, QColor('red') )
        if dlg.exec_():
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if self.is_reset_enabled and e.button() == Qt.RightButton:
            self.setColor(None)
        else:
            return super(QColorButton, self).mousePressEvent(e)


class QNoneDoubleSpinBox(QDoubleSpinBox):
    """
    Custom Qt widget to offer a DoubleSpinBox that can hold null values.

    The value can be set to null with right-click. When set to null the widget
    appears faded.
    """

    def __init__(self, *args, **kwargs):
        super(QNoneDoubleSpinBox, self).__init__(*args, **kwargs)
        self.is_None = False

    def value(self):
        if self.is_None:
            return None
        else:
            return super(QNoneDoubleSpinBox, self).value()

    def setValue(self, v):
        if v is None:
            self.is_None = True
            self.setEnabled(False)
            self.valueChanged.emit(-65535)  # Dummy value
        else:
            self.is_None = False
            self.setEnabled(True)
            super(QNoneDoubleSpinBox, self).setValue(v)

    def event(self, e):
        if (
            type(e) == QContextMenuEvent
        ):  # int and event.button() == QtCore.Qt.RightButton:
            e.accept()
            if self.is_None:
                self.setValue(super(QNoneDoubleSpinBox, self).value())
            else:
                self.setValue(None)
            return True
        else:
            return super(QNoneDoubleSpinBox, self).event(e)


class QListWidgetAddRemove(QListWidget):
    itemAddedOrRemoved = pyqtSignal()

    def addItem(self, *args, **kwargs):
        r = super(QListWidgetAddRemove, self).addItem(*args, **kwargs)
        self.itemAddedOrRemoved.emit()
        return r

    def addItems(self, *args, **kwargs):
        r = super(QListWidgetAddRemove, self).addItems(*args, **kwargs)
        self.itemAddedOrRemoved.emit()
        return r

    def removeItemAt(self, row, *args, **kwargs):
        r = super(QListWidgetAddRemove, self).takeItem(row)
        self.itemAddedOrRemoved.emit()
        return r

    def clear(self, *args, **kwargs):
        r = super(QListWidgetAddRemove, self).clear(*args, **kwargs)
        self.itemAddedOrRemoved.emit()
        return r


class QFileOpenLineEdit(QWidget):
    textChanged = pyqtSignal(object)
    icon = "disk--arrow.png"

    def __init__(
        self,
        parent=None,
        description=tr("Select file"),
        filename_filter=tr("All Files") + " (*.*);;",
        **kwargs,
    ):
        super(QFileOpenLineEdit, self).__init__(parent, **kwargs)

        self._text = None

        self.description = description
        self.filename_filter = filename_filter

        self.lineedit = QLineEdit()
        self.button = QToolButton()
        self.button.setIcon(QIcon(os.path.join(utils.scriptdir, "icons", self.icon)))

        layout = QHBoxLayout(self)
        layout.addWidget(self.lineedit)
        layout.addWidget(self.button, stretch=1)
        self.setLayout(layout)

        self.button.pressed.connect(self.onSelectPath)

        # Reciprocal setting of values; keep in sync
        self.textChanged.connect(self.lineedit.setText)
        self.lineedit.textChanged.connect(self.setText)

    def onSelectPath(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, self.description, "", self.filename_filter
        )
        if filename:
            self.setText(filename)

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text
        self.textChanged.emit(self._text)


class QFileSaveLineEdit(QFileOpenLineEdit):
    icon = "disk--pencil.png"

    def __init__(
        self,
        parent=None,
        description=tr("Select save filename"),
        filename_filter=tr("All Files") + " (*.*);;",
        **kwargs,
    ):
        super(QFileSaveLineEdit, self).__init__(
            parent, description, filename_filter, **kwargs
        )

    def onSelectPath(self):
        filename, _ = QFileDialog.getSaveFileName(
            self.w, self.description, "", self.filename_filter
        )
        if filename:
            self.setText(filename)


class QFolderLineEdit(QFileOpenLineEdit):
    icon = "folder-horizontal-open.png"

    def __init__(
        self, parent=None, description=tr("Select folder"), filename_filter="", **kwargs
    ):
        super(QFolderLineEdit, self).__init__(
            parent, description, filename_filter, **kwargs
        )

    def onSelectPath(self):
        Qd = QFileDialog()
        Qd.setFileMode(QFileDialog.Directory)
        Qd.setOption(QFileDialog.ShowDirsOnly)

        folder = Qd.getExistingDirectory(self, self.description)
        if folder:
            self.setText(folder)


# GENERIC CONFIGURATION AND OPTION HANDLING


# Generic configuration dialog handling class
class GenericDialog(QDialog):
    """
    A generic dialog wrapper that handles most common dialog setup/shutdown functions.

    Support for config, etc. to be added for auto-handling widgets and config load/save.
    """

    def __init__(self, parent, buttons=["ok", "cancel"], **kwargs):
        super(GenericDialog, self).__init__(parent, **kwargs)

        self.sizer = QVBoxLayout()
        self.layout = QVBoxLayout()

        QButtons = {
            "ok": QDialogButtonBox.Ok,
            "cancel": QDialogButtonBox.Cancel,
        }
        Qbtn = 0
        for k in buttons:
            Qbtn = Qbtn | QButtons[k]

        # Setup default button configurations etc.
        self.buttonBox = QDialogButtonBox(Qbtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def dialogFinalise(self):
        self.sizer.addLayout(self.layout)
        self.sizer.addWidget(self.buttonBox)

        # Set dialog layout
        self.setLayout(self.sizer)

    def setListControl(self, control, list, checked):
        # Automatically set List control checked based on current options list
        items = control.GetItems()
        try:
            idxs = [items.index(e) for e in list]
            for idx in idxs:
                if checked:
                    control.Select(idx)
                else:
                    control.Deselect(idx)
        except:
            pass


class DialogAbout(QDialog):
    def __init__(self, parent, **kwargs):
        super(DialogAbout, self).__init__(parent, **kwargs)

        self.setWindowTitle("About NMRbrew")
        self.help = QWebView(self)  # , parent.onBrowserNav)
        with open(os.path.join(utils.basedir, "README.md"), "rU") as f:
            md = f.read()

        html = """<html>
<head><title>About</title><link rel="stylesheet" href="{css}"></head>
<body>
<div class="container" id="notebook-container">
<div class="cell border-box-sizing text_cell rendered">
<div class="inner_cell">
<div class="text_cell_render border-box-sizing rendered_html">{html}</div>
</div>
</div>
</div>
</div>
        </body>
        </html>""".format(
            **{
                "baseurl": "file:///" + os.path.join(utils.scriptdir),
                "css": "file:///" + css,
                "html": markdown2html_mistune(md),
            }
        )

        self.help.setHtml(html, QUrl("file:///" + os.path.join(utils.scriptdir)))
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.help)

        # Setup default button configurations etc.
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttonBox.rejected.connect(self.close)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def sizeHint(self):
        return QSize(600, 600)


class DialogRegister(QDialog):
    def __init__(self, parent, **kwargs):
        super(DialogRegister, self).__init__(parent, **kwargs)

        self.setWindowTitle("Register NMRbrew")

        self.layout = QVBoxLayout()
        self.layout.addWidget(
            QLabel(
                "Please register NMRbrew by entering your details below.\n\nThis is completely optional but helps it helps us find out\nhow NMRbrew is being used."
            )
        )

        self.layout.addSpacerItem(QSpacerItem(0, 20))

        bx = QGridLayout()

        self.name = QLineEdit()
        bx.addWidget(QLabel("Name"), 0, 0)
        bx.addWidget(self.name, 0, 1)

        self.institution = QLineEdit()
        bx.addWidget(QLabel("Institution/Organisation"), 1, 0)
        bx.addWidget(self.institution, 1, 1)

        self.type = QComboBox()
        self.type.addItems(
            [
                "Academic",
                "Governmental",
                "Commercial",
                "Non-profit",
                "Personal",
                "Other",
            ]
        )
        bx.addWidget(QLabel("Type of organisation"), 2, 0)
        bx.addWidget(self.type, 2, 1)

        self.country = QLineEdit()
        bx.addWidget(QLabel("Country"), 3, 0)
        bx.addWidget(self.country, 3, 1)

        self.research = QLineEdit()
        bx.addWidget(QLabel("Research interest"), 4, 0)
        bx.addWidget(self.research, 4, 1)

        self.email = QLineEdit()
        bx.addWidget(QLabel("Email address"), 5, 0)
        bx.addWidget(self.email, 5, 1)

        bx.addItem(QSpacerItem(0, 20), 6, 0)

        self.releases = QComboBox()
        self.releases.addItems(
            ["Check automatically (weekly)", "Subscribe to mailing list", "Don't check"]
        )
        bx.addWidget(QLabel("Software updates"), 7, 0)
        bx.addWidget(self.releases, 7, 1)

        self.layout.addLayout(bx)

        # Setup default button configurations etc.
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.accept)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class ExportImageDialog(GenericDialog):
    """
    Standard dialog to handle image export fromm any view.

    Dialog box presenting a set of options for image export, including dimensions and
    resolution. Resolution is handled as dpm (dots per metre) in keeping with
    internal Qt usage, but convertor functions are available.

    :param parent: Parent window to attach dialog to
    :type QObject: object inherited from QObject
    :param size: Default dimensions for export
    :type size: QSize
    :param dpm: Default dots per metre
    :type dpm: int
    :param show_rerender_options: Show options to re-render/scale output
    :type show_rerender_options: bool

    """

    print_u = {  # Qt uses pixels/meter as it's default resolution so measure relative to meters
        "in": 39.3701,
        "mm": 1000,
        "cm": 100,
        "m": 1,
    }

    print_p = {  # Spinbox parameters dp, increment
        "in": (3, 1, 0.01, 1000),
        "mm": (2, 1, 0.1, 100000),
        "cm": (3, 1, 0.01, 10000),
        "m": (5, 1, 0.0001, 100),
    }

    resolution_u = {  # Qt uses pixels/meter as it's default resolution so scale to that
        "dpi": 39.3701,
        "px/mm": 1000,
        "px/cm": 100,
        "px/m": 1,
    }

    convert_res_to_unit = {"dpi": "in", "px/mm": "mm", "px/cm": "cm", "px/m": "m"}

    def __init__(
        self,
        parent,
        size=QSize(800, 600),
        dpm=11811,
        show_rerender_options=False,
        **kwargs,
    ):
        super(ExportImageDialog, self).__init__(parent, **kwargs)

        self.setWindowTitle(tr("Export Image"))

        # Handle measurements internally as pixels, convert to/from
        self._w = size.width()
        self._h = size.height()
        self.default_print_units = "cm"
        self.default_resolution_units = "dpi"

        self._updating = False

        r = 0
        w = QGridLayout()

        w.addWidget(QLabel("<b>Image Size</b>"), r, 0)
        r += 1

        self.width = QSpinBox()
        self.width.setRange(1, 100000)
        w.addWidget(QLabel("Width"), r, 0)
        w.addWidget(self.width, r, 1)
        r += 1

        self.height = QSpinBox()
        self.height.setRange(1, 100000)
        w.addWidget(QLabel("Height"), r, 0)
        w.addWidget(self.height, r, 1)
        r += 1
        w.addItem(QSpacerItem(1, 10), r, 0)
        r += 1

        w.addWidget(QLabel("<b>Print Size</b>"), r, 0)
        r += 1

        self.width_p = QDoubleSpinBox()
        self.width_p.setRange(0.0001, 10000)
        w.addWidget(QLabel("Width"), r, 0)
        w.addWidget(self.width_p, r, 1)
        r += 1

        self.height_p = QDoubleSpinBox()
        self.height_p.setRange(0.0001, 10000)
        w.addWidget(QLabel("Height"), r, 0)
        w.addWidget(self.height_p, r, 1)

        self.print_units = QComboBox()
        self.print_units.addItems(list(self.print_u.keys()))
        self.print_units.setCurrentIndex(
            self.print_units.findText(self.default_print_units)
        )

        w.addWidget(self.print_units, r, 2)
        r += 1

        self.resolution = QDoubleSpinBox()
        self.resolution.setRange(1, 1000000)
        self.resolution.setValue(300)
        self.resolution.setDecimals(2)

        self.resolution_units = QComboBox()
        self.resolution_units.addItems(list(self.resolution_u.keys()))
        self.resolution_units.setCurrentIndex(
            self.resolution_units.findText(self.default_resolution_units)
        )

        w.addWidget(QLabel("Resolution"), r, 0)
        w.addWidget(self.resolution, r, 1)
        w.addWidget(self.resolution_units, r, 2)
        r += 1
        w.addItem(QSpacerItem(1, 10), r, 0)
        r += 1

        if show_rerender_options:
            w.addWidget(QLabel("<b>Scaling</b>"), r, 0)
            r += 1
            self.scaling = QComboBox()
            self.scaling.addItems(["Resample", "Resize"])
            self.scaling.setCurrentIndex(self.scaling.findText("Resample"))
            w.addWidget(QLabel("Scaling method"), r, 0)
            w.addWidget(self.scaling, r, 1)
            r += 1
            w.addItem(QSpacerItem(1, 20), r, 0)
        else:
            self.scaling = False

        # Set values
        self.width.setValue(self._w)
        self.height.setValue(self._h)
        self.update_print_dimensions()

        # Set event handlers (here so not triggered while setting up)
        self.width.valueChanged.connect(self.changed_image_dimensions)
        self.height.valueChanged.connect(self.changed_image_dimensions)
        self.width_p.valueChanged.connect(self.changed_print_dimensions)
        self.height_p.valueChanged.connect(self.changed_print_dimensions)
        self.resolution_units.currentIndexChanged.connect(self.changed_resolution_units)
        self.resolution.valueChanged.connect(self.changed_print_resolution)
        self.print_units.currentIndexChanged.connect(self.changed_print_units)

        self.layout.addLayout(w)

        self.setMinimumSize(QSize(300, 150))
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)

        self._current_dimension = self.print_units.currentText()
        self._current_resolution = self.resolution.value()
        self._current_resolution_units = self.resolution_units.currentText()

        # Build dialog layout
        self.dialogFinalise()

    def changed_image_dimensions(self):
        if not self._updating:
            self._updating = True
            self.update_print_dimensions()
        self._updating = False

        # Keep internal data synced
        self._w = self.width.value()
        self._h = self.height.value()

    def changed_print_dimensions(self):
        if not self._updating:
            self._updating = True
            self.update_image_dimensions()
        self._updating = False

    def changed_print_resolution(self):
        w_p = self.width_p.value()
        h_p = self.height_p.value()

        new_resolution = self.resolution.value()
        self.width_p.setValue((w_p / self._current_resolution) * new_resolution)
        self.height_p.setValue((h_p / self._current_resolution) * new_resolution)
        self._current_resolution = self.resolution.value()

    def changed_print_units(self):
        dimension_t = self.print_units.currentText()
        for o in [self.height_p, self.width_p]:
            o.setDecimals(self.print_p[dimension_t][0])
            o.setSingleStep(self.print_p[dimension_t][1])
            o.setRange(self.print_p[dimension_t][2], self.print_p[dimension_t][3])

        if dimension_t != self._current_dimension:
            # We've had a change, so convert
            self.width_p.setValue(
                self.get_converted_measurement(
                    self.width_p.value(), self._current_dimension, dimension_t
                )
            )
            self.height_p.setValue(
                self.get_converted_measurement(
                    self.height_p.value(), self._current_dimension, dimension_t
                )
            )

        self._current_dimension = dimension_t

    def changed_resolution_units(self):
        ru = self.resolution_units.currentText()
        self.resolution.setValue(
            self.resolution.value()
            * self.resolution_u[self._current_resolution_units]
            / float(self.resolution_u[ru])
        )
        self._current_resolution_units = ru

    # Update print dimensions using the image dimensions and resolutions
    def update_print_dimensions(self):
        self._w = self.width.value()
        self._h = self.height.value()

        print_units = self.print_units.currentText()
        w_p = self.get_as_print_size(self._w, print_units)
        h_p = self.get_as_print_size(self._h, print_units)

        self.width_p.setValue(w_p)
        self.height_p.setValue(h_p)

    def get_as_print_size(self, s, u):
        ps = self.resolution.value()
        ps_u = self.resolution_units.currentText()
        s = s / (ps * self.resolution_u[ps_u])  # Get size in metres
        return self.get_converted_measurement(s, "m", u)  # Return converted value

    def get_print_size(self, u):
        return (self.get_as_print_size(self._w, u), self.get_as_print_size(self._h, u))

    # Update image dimensions using the print dimensions and resolutions
    def update_image_dimensions(self):
        w_p = self.width_p.value()
        h_p = self.height_p.value()

        print_units = self.print_units.currentText()
        resolution = self.resolution.value()
        resolution_units = self.resolution_units.currentText()

        self._w = self.get_pixel_size(w_p, print_units, resolution, resolution_units)
        self._h = self.get_pixel_size(h_p, print_units, resolution, resolution_units)

        self.width.setValue(self._w)
        self.height.setValue(self._h)

    def get_pixel_size(self, s, pu, r, ru):
        s = s / self.print_u[pu]  # Convert to metres
        rm = r * self.resolution_u[ru]  # Dots per metre
        return s * rm

    def get_converted_measurement(self, x, f, t):
        # Convert measurement from f to t
        f = self.print_u[f]
        t = self.print_u[t]
        return (float(x) / float(f)) * t

    def get_pixel_dimensions(self):
        return QSize(self._w, self._h)

    def get_dots_per_meter(self):
        return (
            self.resolution.value()
            * self.resolution_u[self.resolution_units.currentText()]
        )

    def get_dots_per_inch(self):
        if self.resolution_units.currentText() == "in":
            return self.resolution.value()
        else:
            return self.get_converted_measurement(
                self.resolution.value(),
                self.convert_res_to_unit[self.resolution_units.currentText()],
                "in",
            )

    def get_resample(self):
        if self.scaling:
            return self.scaling.currentText() == "Resample"
        else:
            return False


class ToolListDelegate(QAbstractItemDelegate):
    def paint(self, painter, option, index):
        r = option.rect

        # item.setData(Qt.DisplayRole, "%s" % job.name)
        # item.setData(Qt.UserRole, "%d/%d complete; %d error(s)" % (e_complete, e_total, e_errored))
        # item.setData(Qt.UserRole + 3, job.status)
        # item.setData(Qt.UserRole + 2, float(e_complete)/float(e_total))

        # GET TITLE, DESCRIPTION
        title = index.data(Qt.DisplayRole)  # .toString()
        icon = index.data(Qt.DecorationRole)
        tool = index.data(Qt.UserRole)  # .toString()
        description = index.data(Qt.UserRole + 1)  # .toString()

        progress = index.data(Qt.UserRole + 2)
        status = index.data(Qt.UserRole + 3)

        text_color = QPalette().text().color()

        c = STATUS_QCOLORS[status]
        if option.state & QStyle.State_Selected:
            painter.setPen(QPalette().highlightedText().color())
            if status == "ready":
                c = QPalette().highlight().color()
            else:
                c.setAlpha(60)

        else:
            if status == "inactive":
                text_color.setAlpha(100)

            c.setAlpha(30)

        painter.fillRect(r, QBrush(c))

        # ICON
        r = option.rect.adjusted(5, 5, -10, -10)
        icon.paint(painter, r, Qt.AlignVCenter | Qt.AlignLeft)

        font = painter.font()
        font.setPointSize(10)

        font.setWeight(QFont.Bold)
        painter.setFont(font)

        # TITLE
        r = option.rect.adjusted(40, 5, 0, 0)
        pen = QPen()
        pen.setColor(text_color)
        painter.setPen(pen)
        painter.drawText(r.left(), r.top(), r.width(), r.height(), Qt.AlignLeft, title)

        font.setWeight(QFont.Normal)
        painter.setFont(font)

        # DESCRIPTION
        r = option.rect.adjusted(40, 18, 0, 0)
        painter.drawText(
            r.left(), r.top(), r.width(), r.height(), Qt.AlignLeft, description
        )

        painter.setRenderHint(QPainter.Antialiasing)

        status_r = QRectF(
            215, option.rect.y() + (option.rect.height() / 2) - 12.5, 25, 25
        )
        if tool.current_status == "active":
            pen = QPen()
            c = STATUS_QCOLORS[status]
            c.setAlpha(100)
            pen.setColor(c)
            pen.setWidth(5)

            painter.setPen(pen)

            painter.drawArc(status_r, 1440, -(5760 * tool.current_progress))

        else:
            pass

    def sizeHint(self, option, index):
        return QSize(200, 40)


class ToolListWidget(QListWidget):
    def __init__(self, parent=None, **kwargs):
        super(ToolListWidget, self).__init__(parent, **kwargs)

        # self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setItemDelegate(ToolListDelegate(self))
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.customContextMenuRequested.connect(self.showContext)

    def showContext(self, pos):
        item = self.itemAt(pos)

        cx = QMenu("Context menu")
        if item.tool.current_status == "inactive":
            act = QAction("Activate", self)
            act.triggered.connect(item.tool.activate)
            cx.addAction(act)
        else:
            act = QAction("Disable", self)
            act.triggered.connect(item.tool.disable)
            cx.addAction(act)

        cx.exec_(self.mapToGlobal(pos))


class AnnotateClasses(GenericDialog):
    def __init__(self, parent, config=None, *args, **kwargs):
        super(AnnotateClasses, self).__init__(parent, *args, **kwargs)

        self.setWindowTitle("Annotate Classes")

        if config:
            # Copy in starting state
            self.config = ConfigManager()
            self.config.hooks.update(custom_pyqtconfig_hooks.items())

            self.config.set_defaults(config)

        self.fwd_map_cache = {}

        # Correlation variables
        gb = QGroupBox("Sample classes")
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.lw_classes = QListWidgetAddRemove()
        self.lw_classes.setSelectionMode(QAbstractItemView.ExtendedSelection)
        vbox.addWidget(self.lw_classes)

        vboxh = QHBoxLayout()

        self.add_label = QLineEdit()
        self.add_class = QLineEdit()

        addc = QPushButton("Add")
        addc.clicked.connect(self.onClassAdd)

        remc = QPushButton("Remove selected")
        remc.clicked.connect(self.onClassAdd)

        loadc = QPushButton("Import from file")
        loadc.setIcon(
            QIcon(os.path.join(utils.scriptdir, "icons", "folder-open-document.png"))
        )
        loadc.clicked.connect(self.onClassImport)

        vboxh.addWidget(self.add_label)
        vboxh.addWidget(self.add_class)
        vboxh.addWidget(addc)

        vbox.addWidget(remc)
        vbox.addLayout(vboxh)
        vboxh.addWidget(loadc)

        gb.setLayout(vbox)

        self.layout.addWidget(gb)

        self.config.add_handler(
            "annotation/sample_classes",
            self.lw_classes,
            (self.map_list_fwd, self.map_list_rev),
        )

        self.dialogFinalise()

    def onClassAdd(self):
        c = self.config.get("annotation/sample_classes")[
            :
        ]  # Create new list to force refresh on reassign
        c.append((self.add_label.text(), self.add_class.text()))
        self.config.set("annotation/sample_classes", c)

    def onClassRemove(self):
        i = self.lw_classes.removeItemAt(self.lw_classes.currentRow())
        # c = self.map_list_fwd(i.text())

    def onClassImport(self):
        filename, _ = QFileDialog.getOpenFileName(
            self.parent(),
            "Load classifications from file",
            "",
            "All compatible files (*.csv *.txt *.tsv);;Comma Separated Values (*.csv);;Plain Text Files (*.txt);;Tab Separated Values (*.tsv);;All files (*.*)",
        )
        if filename:
            c = self.config.get("annotation/sample_classes")[
                :
            ]  # Create new list to force refresh on reassign

            with open(filename, "rU") as f:
                reader = csv.reader(f, delimiter=b",", dialect="excel")
                for row in reader:
                    if row not in c:
                        c.append(row[:2])

            self.config.set("annotation/sample_classes", c)

    def map_list_fwd(self, s):
        "Receive text name, return the indexes"
        return self.fwd_map_cache[s]

    def map_list_rev(self, x):
        "Receive the indexes, return the label"
        s = "%s\t%s" % tuple(x)
        self.fwd_map_cache[s] = x
        return s


class AnnotatePeaks(GenericDialog):
    def __init__(self, parent, config=None, *args, **kwargs):
        super(AnnotatePeaks, self).__init__(parent, *args, **kwargs)

        self.setWindowTitle("Annotate Peaks")

        if config:
            # Copy in starting state
            self.config = ConfigManager()
            self.config.hooks.update(custom_pyqtconfig_hooks.items())

            self.config.set_defaults(config)

        self.fwd_map_cache = {}

        # Correlation variables
        gb = QGroupBox("Peaks")
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.lw_peaks = QListWidgetAddRemove()
        self.lw_peaks.setSelectionMode(QAbstractItemView.ExtendedSelection)
        vbox.addWidget(self.lw_peaks)

        vboxh = QHBoxLayout()

        self.add_label = QLineEdit()
        self.add_start = QDoubleSpinBox()
        self.add_start.setRange(-1, 12)
        self.add_start.setDecimals(3)
        self.add_start.setSuffix("ppm")
        self.add_start.setSingleStep(0.001)

        self.add_end = QDoubleSpinBox()
        self.add_end.setRange(-1, 12)
        self.add_end.setDecimals(3)
        self.add_end.setSuffix("ppm")
        self.add_end.setSingleStep(0.001)

        addc = QPushButton("Add")
        addc.clicked.connect(self.onPeakAdd)

        remc = QPushButton("Remove selected")
        remc.clicked.connect(self.onPeakAdd)

        loadc = QPushButton("Import from file")
        loadc.setIcon(
            QIcon(os.path.join(utils.scriptdir, "icons", "folder-open-document.png"))
        )
        loadc.clicked.connect(self.onPeakImport)

        metabh = QPushButton("Auto match via MetaboHunter")
        metabh.setIcon(
            QIcon(os.path.join(utils.scriptdir, "icons", "metabohunter.png"))
        )
        metabh.clicked.connect(self.onPeakImportMetabohunter)

        vboxh.addWidget(self.add_label)
        vboxh.addWidget(self.add_start)
        vboxh.addWidget(self.add_end)

        vboxh.addWidget(addc)

        vbox.addWidget(remc)
        vbox.addLayout(vboxh)
        vbox.addWidget(loadc)
        vbox.addWidget(metabh)

        gb.setLayout(vbox)

        self.layout.addWidget(gb)

        self.config.add_handler(
            "annotation/peaks", self.lw_peaks, (self.map_list_fwd, self.map_list_rev)
        )

        self.dialogFinalise()

    def onPeakAdd(self):
        c = self.config.get("annotation/peaks")[
            :
        ]  # Create new list to force refresh on reassign
        c.append(
            (
                self.add_label.text(),
                float(self.add_start.value()),
                float(self.add_end.value()),
            )
        )
        self.config.set("annotation/peaks", c)

    def onPeakRemove(self):
        i = self.lw_peaks.removeItemAt(self.lw_peaks.currentRow())
        # c = self.map_list_fwd(i.text())

    def onPeakImport(self):
        filename, _ = QFileDialog.getOpenFileName(
            self.parent(),
            "Load peak annotations from file",
            "",
            "All compatible files (*.csv *.txt *.tsv);;Comma Separated Values (*.csv);;Plain Text Files (*.txt);;Tab Separated Values (*.tsv);;All files (*.*)",
        )
        if filename:
            c = self.config.get("annotation/peaks")[
                :
            ]  # Create new list to force refresh on reassign

            with open(filename, "rU") as f:
                reader = csv.reader(f, delimiter=b",", dialect="excel")
                for row in reader:
                    if row not in c:
                        c.append(row[0], float(row[1]), float(row[2]))

            self.config.set("annotation/peaks", c)

    def onPeakImportMetabohunter(self):
        c = self.config.get("annotation/peaks")[
            :
        ]  # Create new list to force refresh on reassign
        t = self.parent().current_tool

        dlg = MetaboHunter(self)
        if dlg.exec_():
            if "spc" in t.data:
                # We have a spectra; calcuate mean; reduce size if required
                spc = t.data["spc"]
                n = spc.data.shape[1]
                ppm = spc.ppm
                spcd = np.mean(spc.data, axis=0)

                # Set a hard limit on the size of data we submit to be nice.
                if n > 3000:
                    # Calculate the division required to be under the limit
                    d = np.ceil(float(n) / 3000)
                    # Trim axis to multiple of divisor
                    trim = (n // d) * d
                    spcd = spcd[:trim]
                    ppm = ppm[:trim]
                    # Mean d shape
                    spcd = np.mean(spcd.reshape(-1, d), axis=1)
                    ppm = np.mean(ppm.reshape(-1, d), axis=1)

            # Submit with settings
            hmdbs = metabohunter.request(
                ppm,
                spcd,
                metabotype=dlg.config.get("Metabotype"),
                database=dlg.config.get("Database Source"),
                ph=dlg.config.get("Sample pH"),
                solvent=dlg.config.get("Solvent"),
                frequency=dlg.config.get("Frequency"),
                method=dlg.config.get("Method"),
                noise=dlg.config.get("Noise Threshold"),
                confidence=dlg.config.get("Confidence Threshold"),
                tolerance=dlg.config.get("Tolerance"),
            )

            ha = np.array(hmdbs)
            unique_hmdbs = set(hmdbs)
            if None in unique_hmdbs:
                unique_hmdbs.remove(None)

            # Extract out regions
            for hmdb in unique_hmdbs:
                hb = np.diff(ha == hmdb)

                # These are needed to ensure markers are there for objects starting and ending on array edge
                if ha[0] == hmdb:
                    hb[0] == True

                if ha[-1] == hmdb:
                    hb[-1] == True

                idx = np.nonzero(hb)[0]
                idx = idx.reshape(-1, 2)

                if (
                    dlg.config.get("convert_hmdb_ids_to_names")
                    and hmdb in METABOHUNTER_HMDB_NAME_MAP.keys()
                ):
                    label = METABOHUNTER_HMDB_NAME_MAP[hmdb]
                else:
                    label = hmdb

                # Now we have an array of all start, stop positions for this item
                for start, stop in idx:
                    c.append((label, ppm[start], ppm[stop]))

        self.config.set("annotation/peaks", c)

    def map_list_fwd(self, s):
        "Receive text name, return the indexes"
        return self.fwd_map_cache[s]

    def map_list_rev(self, x):
        "Receive the indexes, return the label"
        s = "%s\t%.2f\t%.2f" % tuple(x)
        self.fwd_map_cache[s] = x
        return s


class Preferences(GenericDialog):
    """
    Application preferences dialog. This is passed a set of options and these are duplicated-stored internally.
    If the preferences dialog is exited with OK, these changes are copied and applied back to the
    global settings object. If exited with Cancel they are discarded.

    """

    def __init__(self, parent, config=None, *args, **kwargs):
        super(Preferences, self).__init__(parent, *args, **kwargs)

        if config:
            # Copy in starting state
            self.config = ConfigManager()
            self.config.hooks.update(custom_pyqtconfig_hooks.items())
            self.config.set_defaults(config)

        self.dialogFinalise()


# Dialog box for Metabohunter search options
class MetaboHunter(GenericDialog):
    options = {
        "Metabotype": {
            "All": "All",
            "Drug": "Drug",
            "Food additive": "Food additive",
            "Mammalian": "Mammalian",
            "Microbial": "Microbial",
            "Plant": "Plant",
            "Synthetic/Industrial chemical": "Synthetic/Industrial chemical",
        },
        "Database Source": {
            "Human Metabolome Database (HMDB)": "HMDB",
            "Madison Metabolomics Consortium Database (MMCD)": "MMCD",
        },
        "Sample pH": {
            "10.00 - 10.99": "ph7",
            "7.00 - 9.99": "ph7",
            "6.00 - 6.99": "ph6",
            "5.00 - 5.99": "ph5",
            "4.00 - 4.99": "ph4",
            "3.00 - 3.99": "ph3",
        },
        "Solvent": {
            "All": "all",
            "Water": "water",
            "CDCl3": "cdcl3",
            "CD3OD": "5d3od",
            "5% DMSO": "5dmso",
        },
        "Frequency": {
            "All": "all",
            "600 MHz": "600",
            "500 MHz": "500",
            "400 MHz": "400",
        },
        "Method": {
            "MH1: Highest number of matched peaks": "HighestNumber",
            "MH2: Highest number of matched peaks with shift tolerance": "HighestNumberNeighbourhood",
            "MH3: Greedy selection of metabolites with disjoint peaks": "Greedy2",
            "MH4: Highest number of matched peaks with intensities": "HighestNumberHeights",
            "MH5: Greedy selection of metabolites with disjoint peaks and heights": "Greedy2Heights",
        },
    }

    def __init__(self, *args, **kwargs):
        super(MetaboHunter, self).__init__(*args, **kwargs)

        self.setWindowTitle("MetaboHunter")
        # Copy in starting state
        self.config = ConfigManager()
        self.config.hooks.update(custom_pyqtconfig_hooks.items())

        self.config.set_defaults(
            {
                "Metabotype": "All",
                "Database Source": "HMDB",
                "Sample pH": "ph7",
                "Solvent": "water",
                "Frequency": "all",
                "Method": "HighestNumberNeighbourhood",
                "Noise Threshold": 0.0001,
                "Confidence Threshold": 0.5,
                "Tolerance": 0.1,
                "convert_hmdb_ids_to_names": True,
            }
        )

        self.lw_combos = {}

        for o in [
            "Metabotype",
            "Database Source",
            "Sample pH",
            "Solvent",
            "Frequency",
            "Method",
        ]:
            row = QVBoxLayout()
            cl = QLabel(o)
            cb = QComboBox()

            cb.addItems(list(self.options[o].keys()))
            row.addWidget(cl)
            row.addWidget(cb)
            self.config.add_handler(o, cb, self.options[o])

            self.layout.addLayout(row)

        row = QGridLayout()
        self.lw_spin = {}
        for n, o in enumerate(["Noise Threshold", "Confidence Threshold", "Tolerance"]):
            cl = QLabel(o)
            cb = QDoubleSpinBox()
            cb.setDecimals(4)
            cb.setRange(0, 1)
            cb.setSingleStep(0.01)
            cb.setValue(float(self.config.get(o)))
            row.addWidget(cl, 0, n)
            row.addWidget(cb, 1, n)

            self.config.add_handler(o, cb)

        self.layout.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Convert HMDB IDs to chemical names?"))
        conv = QCheckBox()
        self.config.add_handler("convert_hmdb_ids_to_names", conv)
        row.addWidget(conv)

        self.layout.addLayout(row)

        self.dialogFinalise()
