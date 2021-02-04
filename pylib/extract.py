"""

"""

from functools import reduce
from itertools import chain
from pathlib import Path

import metapack as mp
import pandas as pd
from demosearch import FileCache
from tqdm.notebook import tqdm


import logging

logger = logging.getLogger(__name__)

class LPError(Exception):
    pass


aggregates = {
    'male_u18': ['b01001_003', 'b01001_004', 'b01001_005', 'b01001_006'],
    'female_u18': ['b01001_027', 'b01001_028', 'b01001_029', 'b01001_030'],
    'male_18_40': ['b01001_007', 'b01001_008', 'b01001_009', 'b01001_010', 'b01001_011', 'b01001_012', 'b01001_013'],
    'female_18_40': ['b01001_031', 'b01001_032', 'b01001_033', 'b01001_034', 'b01001_035', 'b01001_036', 'b01001_037'],
    'senior': ['b01001_020', 'b01001_021', 'b01001_022', 'b01001_023', 'b01001_024', 'b01001_025',
               'b01001_044', 'b01001_045', 'b01001_046', 'b01001_047', 'b01001_048', 'b01001_049'],

    'male_18_44_college': ['b15001_009', 'b15001_010', 'b15001_017', 'b15001_018', 'b15001_025', 'b15001_026'],
    'female_18_44_college': ['b15001_050', 'b15001_051', 'b15001_058', 'b15001_059', 'b15001_066', 'b15001_067']
}


def get_columns(pkg):
    """Get the colums from the existing schema"""
    pkg = mp.open_package(pkg.ref)  # Re-open in case it has changed since loaded in this notebook
    return [e['name'] for e in pkg.resource('census_set').columns()]


def munge(v):
    return v.title() \
               .replace('Partner Households By Sex Of Partner  - Households  - Total  -', '') \
               .replace('Total Population  - Total  - ', '') \
               .replace(' Total Population  - Total', 'Total Population') \
               .replace('  - ', ', ')[11:].strip()


def col_f(v):
    return not v[0].endswith('_m90') and not v[0] in ('geoid', 'stusab', 'county', 'name')


class ExtractManager(object):

    def __init__(self, pkg, cache=None):
        self.pkg = pkg
        self.pkg_root = Path(self.pkg.path).parent

        self.cache = FileCache(self.pkg_root.joinpath('data', 'cache'))

        self._frames = None
        self._df = None
        self._agg_map = None
        self._cache = cache

    @property
    def frames(self):
        if self._frames is None:
            logger.info('Collect frames')
            self._frames = [r.dataframe().drop(columns=['stusab', 'county', 'name']) for r in self.pkg.references()]

        return self._frames

    @property
    def census_set(self):

        if self._df is None or True:

            frames = self.frames

            logger.info('Assemble frames in to dataset')
            df = reduce(lambda left, right: left.join(right), frames[1:], frames[0])

            m90_col = [c for c in df.columns if c.endswith('m90')]
            df = df.drop(columns=m90_col)

            logger.info('Make aggregate map')
            rows = []
            for acol, scols in aggregates.items():
                df[acol] = df.loc[:, scols].sum(axis=1)

                for c in scols:
                    rows.append((acol, c, self.column_map[c.upper()]))

            self._agg_map = pd.DataFrame(rows, columns=['agg_column', 'source_col', 'description'])

            cols = get_columns(self.pkg)
            cols.remove('geoid') # geoid is in the index, not the columns

            self._df = df[cols]

        return self._df

    @property
    def column_map(self):

        kv = list(filter(col_f, chain(*[list(e for e in e.title_map.items()) for e in self._frames])))

        return {k: munge(v) for k, v in kv}

    @property
    def agg_map(self):

        if self._agg_map is None:
            _ = self.census_set # Also creates the agg_map

        return self._agg_map

    def update_schema(self):
        pkg = mp.open_package(self.pkg.ref)  # Re-open in case it has changed since loaded in this notebook

        for c in pkg.resource('combined').schema_term.find('Table.Column'):
            if not c.description:
                c.description = self.column_map.get(c.name.upper())

        pkg.write()

    outputs = ('census_set', 'agg_map')

    def build(self, force=False):

        dd = self.pkg_root.joinpath('data')

        if not dd.exists():
            dd.mkdir(parents=True, exist_ok=True)

        for o in self.outputs:
            p = dd.joinpath(o).with_suffix('.csv')
            if not p.exists() or force:
                logger.info(f"Creating {o}{' (forcing)' if force else ''}")
                d = getattr(self,o)
                logger.info(f"Write {o}")
                d.to_csv(p)
            else:
                logger.info(f"{o} already exists")



# update_schema(pkg)
