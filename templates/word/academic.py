"""Academic Word style template: formal, numbered sections, double-spaced."""

STYLE = {
    "name": "academic",
    "heading_font": "Georgia",
    "body_font": "Georgia",
    "mono_font": "Consolas",
    "heading_color": "000000",  # black
    "body_size_pt": 12,
    "heading_sizes_pt": {1: 18, 2: 14, 3: 12.5, 4: 12},
    "line_spacing": 2.0,        # double-spaced
    "space_after_pt": 6,
    "link_color": "000000",
    "margins_in": {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0},
    "table": {
        "header_fill": None,     # no shading — simple black borders
        "header_text": "000000",
        "header_bold": True,
        "alt_fill": None,
        "borders": "all",
        "border_color": "000000",
    },
    # Sections numbered 1., 1.1., 1.1.1. starting at Heading 2 (Heading 1 is the title)
    "heading_numbering": True,
}
