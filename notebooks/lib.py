

import metapack as mp
import pandas as pd
import numpy as np

from tqdm.notebook import tqdm
from demosearch import FileCache
from pathlib import Path

def latlon_to_epsg(lat, lon):
    import math
    utm_band = (math.floor((lon + 180) / 6) % 60) + 1
   
    return  326 + utm_band if lat >= 0 else 327 + utm_band

def group_resources(pkg, group_name):

    return [r for r in pkg.references() if r.props.get('group') == group_name ]
    
def load_group_frames(pkg, group_name):

    frames = {}

    pkg_root = Path(pkg.path).parent
    cache = FileCache(pkg_root.joinpath('cache'))
    
    for r in tqdm(group_resources(pkg, group_name)):
        if r.name not in frames:
            ck = f'frames/{r.name}'
            if not cache.exists(ck):
                df = r.dataframe()
                frames[r.name] = df
                cache.put_df(ck, pd.DataFrame(df))
            else:
                frames[r.name] = cache.get_df(ck)
                
    return frames

def get_group(pkg, group_name):
    # Join them, and exclude common columns
    
    frames = load_group_frames(pkg, group_name)
    
    frv = list(frames.values())
    t = frv[0].join([e.drop(columns=['stusab', 'county', 'name']) for e in frv[1:]])

    m90_cols = [c for c in t.columns if c.endswith('m90')]
    t = t.drop(columns=m90_cols)

    return t

# Columns that need to be added together are listed in the TableCode colum of the
# schema. 

def conform_schema(df, pkg, schema):

    census = pd.DataFrame(index=df.index)

    out_cols = []
    for c in pkg.resource(schema).schema_term.children:
        out_cols.append(c.name)
        cols = [e.strip().lower() for e in c.props.get('tablecode','').split(',') if e.strip() ]
        if len(cols):
            census[c.name] = df[cols].loc[:,cols].sum(axis=1)


    tracts = pkg.resource('tracts').dataframe()
    census = tracts[['geoid','tract_id']].merge(census.reset_index())[out_cols]

    return census


