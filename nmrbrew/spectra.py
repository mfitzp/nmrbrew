from __future__ import unicode_literals
import numpy as np
import math

from .qt import *
from .globals import settings, config, SPECTRUM_COLOR, OUTLIER_COLOR, CLASS_COLORS
import pyqtgraph as pg

SPECTRUM_COLOR = QColor(63, 63, 63, 100)
OUTLIER_COLOR = QColor(255, 0, 0, 255)

''' Brewer colors for spectra labelled by class '''
CLASS_COLORS = [
    QColor(31, 119, 180, 100),
    QColor(255, 127, 14, 100),
    QColor(44, 160, 44, 100),
    QColor(148, 103, 189, 100),
    QColor(140, 86, 75, 100),
    QColor(227, 119, 194, 100),
    QColor(127, 127, 127, 100),
    QColor(188, 189, 34, 100),
    QColor(23, 190, 207),
]

stops = np.r_[-1.0, -0.5, 0.5, 1.0]
colors = np.array([[0, 0, 1, 0.7], [0, 1, 0, 0.2], [0, 0, 0, 0.8], [1, 0, 0, 1.0]])
SCALE_COLOR_MAP = pg.ColorMap(stops, colors)

def locate_nearest(array, value):
    idx = (np.abs(array-value)).argmin()
    return idx


class PeakAnnotationItem(pg.UIGraphicsItem):

    def __init__(self, text, x1, x2, y):
        super(PeakAnnotationItem, self).__init__(self)

        if x1 > x2:
            x2, x1 = x1, x2

        self.x1 = x1
        self.x2 = x2
        self.y = y
        self.xm = float(x1+x2) / 2
        self.xs = x2-x1

        self.color = QColor('purple')
        self.color.setAlpha(200)

        self.textItem = QGraphicsTextItem()
        self.textItem.setParentItem(self)
        self.lastTransform = None

        self.lineItem = QGraphicsPathItem()
        self.lineItem.setParentItem(self)
        self.lineItem.setPen(QPen(self.color))

        self._bounds = QRectF()

        self.textItem.setDefaultTextColor(self.color)
        self.textItem.setPlainText(text)

        f = self.textItem.font()
        f.setPointSizeF(9)
        self.textItem.setFont(f)

        # Apply initial transform to move us above the target
        transform = QTransform()
        transform.translate(0, -5)
        self.setTransform(transform)

        self.setFlag(self.ItemIgnoresTransformations)  ## This is required to keep the text unscaled inside the viewport

        self.setPos(self.xm, y)


    def updateMarker(self):
        # Update the boundary line beneath the text
        t = self.sceneTransform()
        if t is None:
            return

        if self._exportOpts is not False and 'resolutionScale' in self._exportOpts:
            s = self._exportOpts['resolutionScale']
        else:
            s = 1

        self.textItem.resetTransform()
        if s:
            self.textItem.scale(s, s)

        self.textItem.setPos(0,0)
        br = self.textItem.boundingRect()
        apos = self.textItem.mapToParent(QPoint(br.width()*0.5, br.height()))
        self.textItem.setPos(-apos.x(), -apos.y())

        w = t.map(self.x2, self.y)[0] - t.map(self.x1, self.y)[0]

        bl = QPainterPath(QPointF(0,0))
        bl.lineTo(QPointF(0,-12))
        bl.lineTo(QPointF(w,-12))
        bl.lineTo(QPointF(w,0))

        self.lineItem.setPath(bl)

        self.lineItem.resetTransform()
        if s:
            self.lineItem.scale(s, s)

        self.lineItem.setPos(-w*s/2, br.height()*0.5*s)


    def viewRangeChanged(self):
        self.updateMarker()

    def boundingRect(self):
        return self.textItem.mapToParent(self.textItem.boundingRect()).boundingRect()

    def paint(self, p, *args):
        tr = p.transform()
        if self.lastTransform is not None:
            if tr != self.lastTransform:
                self.viewRangeChanged()
        self.lastTransform = tr

        #p.setPen(self.border)
        #p.setBrush(self.fill)
        #p.setRenderHint(p.Antialiasing, True)
        #p.drawPolygon(self.textItem.mapToParent(self.textItem.boundingRect()))



class SpectraViewer(QWidget):

    def __init__(self):
        super(SpectraViewer, self).__init__()

        self.layout = QVBoxLayout()

        self.spectraViewer = pg.PlotWidget()
        # self.spectraViewer.enableAutoRange('bottom', True)
        self.spectraViewer.showGrid(True, True)
        self.spectraViewer.invertX()
        self.spectraViewer.enableAutoRange()
        self.spectraViewer.enableAutoScale()

        self.spectraViewer.setLabel('left', 'rel')
        self.spectraViewer.setLabel('bottom', '1H[ppm]')

        self.overViewer = pg.PlotWidget()
        self.overViewer.invertX()
        self.overViewer.setMaximumHeight(40)
        self.overViewer.enableAutoRange()
        self.overViewer.enableAutoScale()

        self.overViewer.hideAxis('left')
        self.overViewer.hideAxis('bottom')
        self.overViewer.hideButtons()
        self.overViewer.setMenuEnabled(False)
        self.overViewer.setMouseEnabled(False, False)

        self.layout.addWidget(self.spectraViewer)
        self.layout.addWidget(self.overViewer)

        self.overview_region = None

        self.spectraViewer.sigXRangeChanged.connect(self.update_region_overview_plot)

        self.setLayout(self.layout)

    def plot(self, spc, autofit=False):

        canvas = self.spectraViewer
        canvas.clear()


        if spc is None:
            return

        pen = QPen()
        pen.setWidth(0)

        sample_classes = dict(config.get('annotation/sample_classes'))
        class_map = list(set(sample_classes.values()))
        class_colors = {c:CLASS_COLORS[n] for n, c in enumerate(class_map)}

        for n, spectrum in enumerate(spc.data):
            c = spc.classes[n]
            l = spc.labels[n]

            if settings.get('spectra/highlight_outliers') and spc.outliers[n] > 0.5:
                pen.setColor(OUTLIER_COLOR)

            elif settings.get('spectra/highlight_classes') and l in sample_classes.keys():
                c = class_colors[ sample_classes[ l] ]
                pen.setColor(c)

            else:
                pen.setColor(SPECTRUM_COLOR)

            canvas.plot( spc.ppm, np.real(spectrum), pen=pen)

        xlim = spc.xlim()
        ylim = spc.ylim()

        canvas.setLimits(
            xMin=xlim[0],
            xMax=xlim[1],
            yMin=ylim[0],
            yMax=ylim[1],

            minYRange=ylim[1] / 1000,
            minXRange=xlim[1] / 1000,
        )

        if settings.get('spectra/show_peak_annotations'):
            peak_annotations = config.get('annotation/peaks')
            for l, x1, x2 in peak_annotations:

                x1i, x2i = locate_nearest(spc.ppm, x1), locate_nearest(spc.ppm, x2)
                if x1i > x2i:
                    x1i, x2i = x2i, x1i

                print(x1i, x2i)

                y = np.max(spc.data[:,x1i:x2i])

                pa = PeakAnnotationItem(l, x1, x2, y)
                canvas.addItem(pa)

        canvas = self.overViewer
        canvas.clear()

        pen = QPen(SPECTRUM_COLOR)
        pen.setWidth(0)
        canvas.plot(spc.ppm, np.mean( np.real(spc.data), axis=0), pen=pen)

        self.update_region_overview_plot()

        if autofit:
            canvas.setRange(xRange=( np.min(spc.ppm), np.max(spc.ppm) ), yRange=( np.min(spc.data), np.max(spc.data) ), padding=0.1, update=True)





    def update_region_overview_plot(self):
        r = self.spectraViewer.viewRect()
        if self.overview_region:
            self.overViewer.removeItem(self.overview_region)

        self.overview_region = pg.LinearRegionItem(values=[r.x(), r.x()+r.width()], movable=False)
        self.overViewer.addItem(self.overview_region)




class PCAViewer(QWidget):

    def __init__(self):
        super(PCAViewer, self).__init__()

        self.layout = QVBoxLayout()

        self.pcaViewer = pg.PlotWidget()
        self.pcaViewer.showGrid(True, True)
        self.pcaViewer.enableAutoRange()
        self.pcaViewer.enableAutoScale()

        self.layout.addWidget(self.pcaViewer)

        self.setLayout(self.layout)

        self.pcaViewer.setLabel('left', 'Principal component 2')
        self.pcaViewer.setLabel('bottom', 'Principal component 1')

    def plot(self, spc, pca, autofit=True):
        canvas = self.pcaViewer
        canvas.clear()



        sample_classes = dict(config.get('annotation/sample_classes'))
        class_map = list(set(sample_classes.values()))
        class_colors = {c:CLASS_COLORS[n] for n, c in enumerate(class_map)}

        brushes = []

        for n, c in enumerate(spc.classes):
            brush = QBrush()
            l = spc.labels[n]

            if settings.get('spectra/highlight_outliers') and spc.outliers[n] > 0.5:
                c = QColor(OUTLIER_COLOR)

            elif settings.get('spectra/highlight_classes') and l in sample_classes.keys():
                c = class_colors[ sample_classes[ l] ]
                c = QColor(c)
            else:
                c = QColor('grey')

            c.setAlpha(200)
            brushes.append(QBrush(c))

        canvas.plot(pca['scores'][:,0], pca['scores'][:,1], pen=None, symbol='o', symbolBrush=brushes)


        xt = np.max( np.abs( pca['scores'][:,0] ) ) * 1.5
        yt = np.max( np.abs( pca['scores'][:,1] ) ) * 1.5

        canvas.setLimits(
            xMin=-xt,
            xMax=xt,
            yMin=-yt,
            yMax=yt,

            minYRange=yt / 10,
            minXRange=xt / 10,
        )

        #if autofit:
        #    canvas.setRange(xRange=(-xt, xt), yRange=(-yt, yt), padding=0.1, update=True)



class Spectra(object):

    def __init__(self, ppm=None, data=None, dic=None, classes=None, labels=None, outliers=None, metadata=None):

        self.data = data  # 2d np array
        self.ppm = ppm
        self.dic = dic

        self.set_classes(classes)
        self.set_labels(labels)
        self.set_outliers(outliers)

        self.metadata = metadata

        self.peaks = []


    def set_classes(self, classes):
        if classes is None:
            self.classes = [None] * self.data.shape[0]
        else:
            self.classes = classes

        self.classmap = list(set(self.classes))

    def set_labels(self, labels):
        if labels is None:
            self.labels = [None] * self.data.shape[0]
        else:
            self.labels = labels

    def set_outliers(self, outliers):
        if outliers is None:
            self.outliers = [0] * self.data.shape[0]
        else:
            self.outliers = outliers

    @property
    def mean(self):
        return np.mean(self.data, axis=0)

    def xlim(self):
        xmin, xmax = np.min(self.ppm), np.max(self.ppm)
        fuzz = max([abs(xmin), abs(xmax)]) * 0.1
        return xmin-fuzz, xmax+fuzz

    def ylim(self):
        ymin, ymax = np.min(self.data), np.max(self.data)
        fuzz = max([abs(ymin), abs(ymax)]) * 0.1
        return ymin-fuzz, ymax+fuzz



