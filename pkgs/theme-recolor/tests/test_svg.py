import gzip

from theme_recolor import svg


def _mark(value: str) -> str:
    return "#000001"


def test_fill_attribute_and_style_property_are_rewritten() -> None:
    text = '<rect fill="#ff0000" style="stroke:#00ff00;stroke-width:2"/>'
    assert svg.rewrite_text(text, _mark) == (
        '<rect fill="#000001" style="stroke:#000001;stroke-width:2"/>'
    )


def test_colour_scheme_classes_are_left_to_plasma() -> None:
    text = '<path class="ColorScheme-Text" fill="#ff0000"/>'
    assert svg.rewrite_text(text, _mark) == text


def test_hint_elements_are_kept() -> None:
    text = '<rect id="normal-hint-top-margin" style="fill:#ff00ff"/>'
    assert svg.rewrite_text(text, _mark) == text


def test_style_blocks_are_kept() -> None:
    text = '<style id="current-color-scheme">.ColorScheme-Text { color:#232629; }</style>'
    assert svg.rewrite_text(text, _mark) == text


def test_non_colour_attributes_are_kept() -> None:
    text = '<path stroke-width="#1" d="m 0 0" />'
    assert svg.rewrite_text(text, _mark) == text


def test_compressed_files_stay_compressed() -> None:
    data = gzip.compress(b'<svg><rect fill="#ff0000"/></svg>')
    result = svg.recolor(data, _mark)
    assert gzip.decompress(result) == b'<svg><rect fill="#000001"/></svg>'


def test_colors_counts_rewritable_colours_only() -> None:
    data = b'<svg><rect fill="#FF0000"/><rect class="ColorScheme-Text" fill="#00ff00"/></svg>'
    assert dict(svg.colors(data)) == {"#ff0000": 1}
