"""Minimal Word style template: modern, clean, sans-serif, minimal decoration."""

STYLE = {
    "name": "minimal",
    "heading_font": "Arial",    # Helvetica/Arial per spec; Arial is universally available
    "body_font": "Arial",
    "mono_font": "Consolas",
    "heading_color": "333333",  # dark gray
    "body_size_pt": 11,
    "heading_sizes_pt": {1: 20, 2: 15, 3: 12.5, 4: 11.5},
    "line_spacing": 1.3,
    "space_after_pt": 8,
    "link_color": "333333",
    "margins_in": {"top": 0.75, "bottom": 0.75, "left": 0.75, "right": 0.75},
    "table": {
        "header_fill": None,     # no fills — clean
        "header_text": "333333",
        "header_bold": True,
        "alt_fill": None,
        "borders": "horizontal", # minimal: horizontal lines only
        "border_color": "D9D9D9",
    },
    "heading_numbering": False,
}
