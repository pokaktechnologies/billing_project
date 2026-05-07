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
