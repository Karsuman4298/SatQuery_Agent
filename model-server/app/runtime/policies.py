"""Capability registry and deterministic input policies override model suggestions."""
from __future__ import annotations
import math
import re
from app.runtime.contracts import QueryPlan

CAPABILITIES = {
    'vqa': {'tool': 'rs_vqa', 'count': 1, 'operations': ['observe', 'answer', 'verify']},
    'caption': {'tool': 'rs_caption', 'count': 1, 'operations': ['observe', 'caption', 'verify']},
    'grounding': {'tool': 'rs_grounder', 'count': 1, 'operations': ['retrieve_tiles', 'localize', 'segment', 'verify']},
    'change': {'tool': 'temporal_specialist', 'count': 2, 'operations': ['validate_grid', 'compare_dates', 'describe_change', 'verify']},
    'fusion': {'tool': 'optical_sar_specialist', 'count': 2, 'operations': ['validate_grid', 'observe_optical', 'observe_sar', 'joint_interpretation', 'verify']},
}


def choose_task(query, assets):
    if query.task != 'auto': return query.task
    text = query.query.lower()
    if len(assets) == 2:
        return 'fusion' if {a.modality for a in assets} & {'sar'} and len({a.modality for a in assets}) > 1 else 'change'
    if re.search(r'\b(changed?|before|after|increased?|decreased?)\b', text): return 'change'
    if re.search(r'\b(fuse|fusion)\b|optical.*sar|sar.*optical', text): return 'fusion'
    if re.search(r'\b(highlight|segment|outline|mask|locate|ground)\b', text): return 'grounding'
    if re.search(r'\b(describe|caption|summarize)\b', text): return 'caption'
    return 'vqa'


def build_plan(query, assets):
    task = choose_task(query, assets)
    capability = CAPABILITIES[task]
    if len(assets) != capability['count']:
        raise ValueError(f'{task} requires {capability["count"]} image(s).')
    limitations = ['Display previews are not calibrated spectral measurements.',
                   'Model scores are not calibrated accuracy estimates.']
    if len(assets) == 2:
        a, b = assets
        if a.checksum == b.checksum: raise ValueError('Pair contains identical image content.')
        if (a.width, a.height, a.crs) != (b.width, b.height, b.crs):
            raise ValueError('Pair dimensions and CRS must match; co-register first.')
        if a.crs and (len(a.transform) != 6 or len(b.transform) != 6 or not all(
            math.isclose(x, y, rel_tol=0, abs_tol=1e-7) for x, y in zip(a.transform, b.transform))):
            raise ValueError('Pair pixel grids differ; co-register before analysis.')
        if not a.crs and not query.alignment_confirmed:
            raise ValueError('Confirm registration for benchmark pairs without georeferencing.')
        limitations.append('Matching pixel grids do not prove subpixel registration.')
        if task == 'fusion':
            if a.modality not in {'optical', 'multispectral'} or b.modality != 'sar':
                raise ValueError('Fusion requires optical/multispectral first and SAR second.')
            limitations.append('Joint visual interpretation is not calibrated optical–SAR feature fusion.')
        else:
            if a.modality != b.modality: raise ValueError('Temporal pairs require the same modality.')
            if not a.acquisition_time or not b.acquisition_time or a.acquisition_time >= b.acquisition_time:
                raise ValueError('Temporal pairs require ordered acquisition dates: earlier image first.')
    return QueryPlan(task=task, tool=capability['tool'], asset_ids=query.asset_ids,
        operations=capability['operations'], parameters={'max_retries': query.max_retries,
        'click_point': query.click_point, 'preview_max_side': 1024}, limitations=limitations)
