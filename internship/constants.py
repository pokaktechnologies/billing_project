# constants.py
FIELD_CONFIG_DEFAULTS = {
    "text":          {},
    "textarea":      {},
    "rating":        {"max_stars": 5},
    "number":        {"min": None, "max": None, "unit": ""},
    "dropdown":      {"options": []},
    "table":         {"rows": [], "columns": []},
    "checkbox_grid": {"rows": [], "columns": []},
}

FIELD_CONFIG_REQUIRED_KEYS = {
    "rating":        ["max_stars"],
    "number":        ["min", "max", "unit"],
    "dropdown":      ["options"],
    "table":         ["rows", "columns"],
    "checkbox_grid": ["rows", "columns"],
    "text":          [],
    "textarea":      [],
}