"""Documentation fields omitted from browser exports and geometry fingerprints."""


def without_documentation(value):
    if isinstance(value, dict):
        return {key:without_documentation(item) for key,item in value.items()
                if key not in ('note', 'evidence', 'presence', 'basis')
                and not key.endswith('Basis')}
    if isinstance(value, list):
        return [without_documentation(item) for item in value]
    return value
