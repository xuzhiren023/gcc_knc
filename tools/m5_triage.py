"""M5 evidence annotations for S12-19 triage; no collection or native execution.

All modeled times use seconds for explicitly declared fixed work. Sampled CPU
seconds in the original triage are retained but never used as elapsed timing.
"""
import copy
import math

from code_census import validate_program

PROPERTIES = ('control_uncertainty', 'dependency_depth', 'available_independence',
              'memory_behaviour', 'compiler_visibility', 'numerical_contract',
              'runtime_overhead')
LEVELS = ('one_context', 'one_core', 'whole_card', 'whole_application')
OUTCOMES = ('unmodified_source_compiler_gain', 'runtime_assisted_gain',
            'algorithm_or_layout_redesign', 'relaxed_numerics')


def number(value, positive=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0 or (positive and value == 0)):
        raise ValueError('expected finite ' + ('positive' if positive else 'nonnegative') + ' number')
    return value


def require(record, keys):
    for key in keys:
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError('missing evidence field: ' + key)


def bound(model):
    """Take max of independently justified same-work bounds, never their sum.

    Callers derive seconds using counted work and qualified machine inputs.
    Retaining formula/source/assumptions permits review without pretending that
    arbitrary instruction classes share one throughput or one bandwidth roof.
    """
    model = copy.deepcopy(model)
    terms = model.get('terms', {})
    unknown = []
    times = {}
    qualifications = []
    for name in ('dependency_path', 'memory'):
        if terms.get(name) is None:
            unknown.append(name)
    resources = terms.get('resources', {})
    if not resources:
        unknown.append('resources')
    flat = {k: terms[k] for k in ('dependency_path', 'memory') if terms.get(k) is not None}
    flat.update({'resource:' + k: v for k, v in resources.items()})
    if flat or model.get('measurement') or model.get('prediction'):
        require(model, ('work', 'configuration', 'assumptions'))
    for name, term in flat.items():
        if term is None or term.get('seconds') is None:
            unknown.append(name)
            continue
        if term.get('status') == 'not_applicable':
            raise ValueError('inapplicable term cannot supply seconds')
        require(term, ('source', 'formula', 'qualification'))
        if term['qualification'] not in ('conditional', 'rigorous'):
            raise ValueError('invalid bound qualification')
        times[name] = number(term['seconds'])
        qualifications.append(term['qualification'])
    lower = max(times.values()) if times else None
    measured = model.get('measurement')
    prediction = model.get('prediction')
    for observation in (measured, prediction):
        if observation:
            require(observation, ('source',))
            number(observation['seconds'], positive=True)
    seconds = measured['seconds'] if measured else None
    # Missing constraints weaken a bound, but do not invalidate the known terms.
    return dict(model, lower_bound_seconds=lower, unknown_terms=sorted(set(unknown)),
                qualification=('conditional' if 'conditional' in qualifications else
                               'rigorous' if times else 'unknown'),
                gap_seconds=seconds - lower if seconds is not None and lower is not None else None,
                bound_utilization=lower / seconds if seconds and lower is not None else None,
                prediction_ratio=prediction['seconds'] / seconds if seconds and prediction else None,
                term_utilization={k: v / seconds for k, v in times.items()} if seconds else {},
                diagnosis=('audit: measurement below bound' if seconds is not None
                           and lower is not None and seconds < lower else 'not diagnosed'))


def extend(capture, annotations):
    """Add a reviewable method record to every region, preserving attribution."""
    validate_program(capture['program'])
    result = copy.deepcopy(capture)
    style = annotations.get('style', 'unknown')
    if style not in ('H', 'S', 'N', 'C', 'G', 'B', 'unknown'):
        raise ValueError('invalid unit style')
    notes = annotations.get('regions', {})
    if set(notes) - {row['id'] for row in result['rows']}:
        raise ValueError('annotation region absent from captured triage')
    result['m5_style'] = style
    result['m5_protocol'] = 'docs/research/m5-measurement-protocol.md'
    for row in result['rows']:
        note = notes.get(row['id'], {})
        supplied = note.get('properties', {})
        if set(supplied) - set(PROPERTIES):
            raise ValueError('unknown property name')
        properties = {}
        for name in PROPERTIES:
            prop = copy.deepcopy(supplied.get(name, dict(status='unknown', value=None,
                                                        source='not captured by S12-19')))
            if prop.get('status') not in ('verified', 'reported', 'inference', 'unknown', 'not_applicable'):
                raise ValueError('invalid property evidence status')
            require(prop, ('source',))
            if prop['status'] not in ('unknown', 'not_applicable') and prop.get('value') is None:
                raise ValueError('property evidence needs a value')
            properties[name] = prop
        models = note.get('levels', {})
        if set(models) - set(LEVELS):
            raise ValueError('invalid measurement level')
        outcomes = {name: [] for name in OUTCOMES}
        if set(note.get('outcomes', {})) - set(OUTCOMES):
            raise ValueError('invalid outcome label')
        for name, observations in note.get('outcomes', {}).items():
            for observation in observations:
                item = copy.deepcopy(observation)
                if item.get('level') not in LEVELS:
                    raise ValueError('outcome needs a measurement level')
                require(item, ('source', 'configuration', 'work'))
                baseline = number(item['baseline_seconds'], positive=True)
                candidate = number(item['candidate_seconds'], positive=True)
                item['speedup'] = baseline / candidate
                outcomes[name].append(item)
        row['m5'] = dict(properties=properties,
                         levels={level: bound(models.get(level, {})) for level in LEVELS},
                         outcomes=outcomes)
    result['m5_donor_priority'] = donor_priority(annotations.get('donor_margins', []))
    return result


def donor_priority(rows):
    """Smallest observed development margin first; unknowns remain visible."""
    result = copy.deepcopy(rows)
    for row in result:
        validate_program(row['program'])
        require(row, ('source',))
        value = row.get('speedup')
        row['margin'] = number(value, positive=True) - 1 if value is not None else None
    return sorted(result, key=lambda r: (r['margin'] is None,
                                        r['margin'] if r['margin'] is not None else 0,
                                        r['program']))
