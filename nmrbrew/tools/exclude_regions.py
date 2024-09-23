import pyqtgraph as pg

from ..qt import *
from ..ui import ConfigPanel, QListWidgetAddRemove
from .base import ToolBase


class ExcludeRegionsConfig(ConfigPanel):
    """Automatic config panel for selecting regions in data, e.g. for icoshift

    This simple config panel lists currently defined data regions, currently defineable
    via drag-drop in output views. Manual definition should also be possible.
    """

    def __init__(self, *args, **kwargs):
        super(ExcludeRegionsConfig, self).__init__(*args, **kwargs)

        self.fwd_map_cache = {}

        # Correlation variables
        gb = QGroupBox("Regions")
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.lw_variables = QListWidgetAddRemove()
        self.lw_variables.setSelectionMode(QAbstractItemView.ExtendedSelection)
        vbox.addWidget(self.lw_variables)

        vboxh = QHBoxLayout()

        addr = QPushButton("Add")
        addr.clicked.connect(self.onRegionAdd)

        remr = QPushButton("Remove")
        remr.clicked.connect(self.onRegionRemove)

        vboxh.addWidget(addr)
        vboxh.addWidget(remr)
        vbox.addLayout(vboxh)

        gb.setLayout(vbox)
        self.layout.addWidget(gb)

        # self.config.add_handler('selected_data_regions', self.lw_variables, (self.map_list_fwd, self.map_list_rev))

        self.finalise()

    def onRegionAdd(self):
        c = self.config.get("selected_data_regions")
        name = "Region %d" % (len(c))
        c.append([name, 4, 6])
        self.config.set(
            "selected_data_regions", c
        )  # FIXME: Need to trigger a refresh here?

        self.tool.add_region(name, 4, 6)

    def onRegionRemove(self):
        i = self.lw_variables.removeItemAt(self.lw_variables.currentRow())
        c = self.map_list_fwd(i.text())
        self.tool.remove_region(c[0])

    def map_list_fwd(self, s):
        "Receive text name, return the indexes"
        return self.fwd_map_cache[s]

    def map_list_rev(self, x):
        "Receive the indexes, return the label"
        s = "%s\t%.2f\t%.2f" % tuple(x)
        self.fwd_map_cache[s] = x
        return s


class ExcludeRegions(ToolBase):
    name = "Exclude regions"
    description = "Remove useless regions"
    icon = "exclude_regions.png"

    def __init__(self, *args, **kwargs):
        super(ExcludeRegions, self).__init__(*args, **kwargs)

        # Define default settings for pathway rendering
        self.config.set_defaults(
            {
                "selected_data_regions": [
                    ("TMSP", -2, 0.2),
                    ("Water", 4.5, 5),
                    ("Far", 10, 12),
                ],
            }
        )

        self.addConfigPanel(ExcludeRegionsConfig)
        self.addButtonBar(self.deftaultButtons())

        self._region_lookup_ = {}

    def run_manual(self):
        self.run(self.exclude)

    @staticmethod
    def exclude(spc, config, progress_callback):
        import numpy as np

        max_ppm = max(spc.ppm)
        min_ppm = min(spc.ppm)

        regions = []
        index_mask = np.arange(spc.data.shape[1])

        def locate_nearest(array, value):
            idx = (np.abs(array - value)).argmin()
            return idx

        for region in config["selected_data_regions"]:
            _, start_ppm, end_ppm = region

            if start_ppm < min_ppm:
                start_ppm = min_ppm

            if end_ppm > max_ppm:
                end_ppm = max_ppm

            if start_ppm < end_ppm:
                start_ppm, end_ppm = end_ppm, start_ppm

            # Convert ppm to nearest index
            start_idx = locate_nearest(spc.ppm, start_ppm)
            end_idx = locate_nearest(spc.ppm, end_ppm)

            if start_idx > end_idx:
                start_idx, end_idx = end_idx, start_idx

            index_mask = index_mask[
                ~np.logical_and(index_mask > start_idx, index_mask < end_idx)
            ]
            regions.append((start_ppm, end_ppm))

        spc.ppm = spc.ppm[index_mask]
        spc.data = spc.data[:, index_mask]

        return {"spc": spc, "regions": regions}

    def add_region(self, name, x1, x2):
        canvas = self.parent().spectraViewer.spectraViewer

        c = QColor("red")
        c.setAlpha(50)

        lri = pg.LinearRegionItem(values=[x1, x2], movable=True, brush=QBrush(c))
        canvas.addItem(lri)
        lri.sigRegionChanged.connect(
            lambda lri, name=name: self.region_change_callback(name, lri)
        )
        self._region_lookup_[name] = lri

    def remove_region(self, name):
        canvas = self.parent().spectraViewer.spectraViewer

        lri = self._region_lookup_[name]
        canvas.removeItem(lri)

    def region_change_callback(self, name, lri):
        conf = []
        for rname, x_start, x_end in self.config.get("selected_data_regions"):
            if rname == name:
                x_start, x_end = lri.getRegion()
            conf.append((rname, x_start, x_end))
        self.config.set("selected_data_regions", conf)

    def plot(self, **kwargs):
        super(ExcludeRegions, self).plot(**kwargs)

        for name, x1, x2 in self.config.get("selected_data_regions"):
            self.add_region(name, x1, x2)
