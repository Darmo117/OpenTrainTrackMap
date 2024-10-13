"""This script parses the imagery index file built by the OSM Editor Layer Index project
into a JSON file for use by the map editor.
The file can be found at <https://github.com/osmlab/editor-layer-index/blob/gh-pages/imagery.xml>.

The index file’s structure is defined at <http://josm.openstreetmap.de/maps-1.0>.
"""
import json
import re
import traceback
from xml.etree import ElementTree

import requests

REQUIRED_ENTRY_TAGS = [
    'name',
    'id',
    'url',
    'category',
]

# Bing imagery is ignored as we do not have the rights to use it.
# scanex, mvt, and html are ignored as I don’t know what they correspond to.
# wms and wmts are ignored as they do not feature any {z}, {x}, and {y} placeholders.
VALID_TYPES = ('tms',)
# qa is ignored as it’s of no use for our purposes
CATEGORIES = ('photo', 'elevation', 'map', 'historicmap', 'osmbasedmap', 'historicphoto', 'other')
DEFAULT_IDS = (
    'MAPNIK',  # Default OSM map style
    'EsriWorldImagery',
)
PLACEHOLDER_PATTERN = re.compile(r'{[^}]*}')
ALLOWED_PLACEHOLDERS_PATTERN = re.compile(r'{([xy]|zoom|switch:\w*(,\w*)*)}')


class Skip(Exception):
    """This exception indicates that the current entry must be skipped."""
    pass


def tag_name(element: ElementTree.Element) -> str:
    """Return the name of the given XML tag without its prefix and namespace."""
    return element.tag.split('}', 1)[1]


def ensure_unique(key: str, d: dict) -> None:
    """Raise an error if the given key is in the given dict.

    :raises KeyError: If the key is already in the dict.
    """
    if key in d:
        raise KeyError(f'duplicate key "{key}"')


def parse_zoom(text: str) -> int:
    """Parse the given zoom value.

    :param text: The text to parse.
    :return: The parsed zoom value.
    """
    return min(max(int(text), 0), 24)


def parse_bounds(bounds_tag: ElementTree.Element) -> dict:
    """Parse the given bounds tag.

    :param bounds_tag: The element to parse.
    :return: A dict containing the parsed bounds.
    """
    shapes = []

    for shape_tag in bounds_tag:
        shape = []
        for point_tag in shape_tag:
            shape.append({
                'lat': float(point_tag.attrib['lat']),
                'lon': float(point_tag.attrib['lon']),
            })
        shapes.append(shape)

    return {
        'bbox': {
            'minLat': float(bounds_tag.attrib['min-lat']),
            'maxLat': float(bounds_tag.attrib['max-lat']),
            'minLon': float(bounds_tag.attrib['min-lon']),
            'maxLon': float(bounds_tag.attrib['max-lon']),
        },
        'shapes': shapes,
    }


def parse_date(text: str) -> dict | None:
    """Parse a date in the form "YYYY-MM-DD;YYYY-MM-DD".
    Each element after first year is optional, a single "-" marks an unknown or open timespan like "-;2015".

    :param text: The text to parse.
    :return: A dict containing the parsed date.
        If the text represents a single date, the 'type' key will have the value 'date'
        and the date will be found at the key 'date'.
        If the text represents an interval, the 'type' key will have the value 'interval'
        and the first date will be found at the key 'start' and the second date will be found at the key 'end'.
    """

    def parse(d: str) -> str | None:
        if d == '-':
            return None
        if re.match(r'\d{4}(-\d{2}-(\d{2})?)?', d):
            return d
        raise ValueError(f'invalid date: {d}')

    if ';' in text:
        date1, date2 = text.split(';')
        data = {'type': 'interval'}
        any_date = False
        if d1 := parse(date1):
            data['start'] = d1
            any_date = True
        if d2 := parse(date2):
            data['end'] = d2
            any_date = True
        return data if any_date else None

    date = parse(text)
    if not date:
        return None
    return {
        'type': 'date',
        'date': date,
    }


def transform_url_placeholders(url: str) -> str:
    """Adapt URL placeholder to fit the format expected by Maplibre.

    :param url: The URL to transform.
    :return: The transformed URL.
    """
    if '{apikey}' in url.lower():
        raise Skip('API key required')
    for match in PLACEHOLDER_PATTERN.findall(url):
        if not ALLOWED_PLACEHOLDERS_PATTERN.match(match):
            raise Skip(f'unsupported tag found: {match}')
    return url.replace('{zoom}', '{z}')


def invalid_value_error(key: str, value) -> ValueError:
    """Return a ValueError for the given key and value."""
    return ValueError(f'invalid {key}: {value}')


def parse_entry(entry_tag: ElementTree.Element, ignored_tiles_sources: dict[str, str]) -> dict:
    """Parse the given <entry> tag.

    :param entry_tag: The tag to parse.
    :return: A dict containing the parsed entry.
    """
    if (attr := 'overlay') in entry_tag.attrib and entry_tag.attrib[attr] == 'true':
        raise Skip('entry is an overlay')

    entry = {}

    # TODO find what this attribute means
    if (attr := 'eli-best') in entry_tag.attrib and entry_tag.attrib[attr] == 'true':
        entry[attr] = True

    for child in entry_tag:
        match tag_name(child):
            # We don’t want to bother with checking terms of use.
            case 'eula' | 'terms-of-use-text' | 'terms-of-use-url':
                raise Skip('imagery has a terms of use')

            case 'name' as key:
                ensure_unique(key, entry)
                entry[key] = child.text

            case 'description' as key:
                if key not in entry:
                    entry[key] = {}
                desc_lang = child.attrib['lang']
                entry[key][desc_lang] = child.text

            case 'id' as key:
                ensure_unique(key, entry)
                text = child.text
                if text in ignored_tiles_sources:
                    raise Skip(f'ignored tiles source {text!r}: {ignored_tiles_sources[text]}')
                entry[key] = text
                if text in DEFAULT_IDS:
                    entry['defaultForType'] = True

            # Can be bing, scanex, mvt, tms, wms, wmts, or html.
            case 'type' as key:
                ensure_unique(key, entry)
                text = child.text
                if text not in VALID_TYPES:
                    raise Skip(f'type is {text!r}')

            case 'url' as key:
                ensure_unique(key, entry)
                entry[key] = transform_url_placeholders(child.text)

            case 'min-zoom' as key:
                ensure_unique(key, entry)
                zoom = parse_zoom(child.text)
                if zoom > 0:
                    entry['minZoom'] = zoom

            case 'max-zoom' as key:
                ensure_unique(key, entry)
                entry['maxZoom'] = parse_zoom(child.text)

            # The area of use.
            case 'bounds' as key:
                ensure_unique(key, entry)
                entry[key] = parse_bounds(child)

            case 'privacy-policy-url' as key:
                ensure_unique(key, entry)
                entry['privacyPolicyUrl'] = child.text

            # A source that this background can be used for OSM.
            case 'permission-ref' as key:
                ensure_unique(key, entry)
                entry['permissionRef'] = child.text

            case 'attribution-text' as key:
                ensure_unique(key, entry)
                # No need to check the 'mandatory' attribute, we keep it anyway.
                entry['attributionText'] = child.text

            # A link that is opened, when the user clicks on the attribution text.
            case 'attribution-url' as key:
                ensure_unique(key, entry)
                entry['attributionUrl'] = child.text

            case 'category' as key:
                ensure_unique(key, entry)
                text = child.text
                if text not in CATEGORIES:
                    raise invalid_value_error(key, text)
                entry[key] = text

            # Schema says its a Base64-encoded image, but the actual file contains only URLs.
            case 'icon' as key:
                ensure_unique(key, entry)
                entry[key] = child.text

            # Date in the form "YYYY-MM-DD;YYYY-MM-DD".
            case 'date' as key:
                ensure_unique(key, entry)
                if date := parse_date(child.text):
                    entry[key] = date

            # Tile size provided by imagery source. Default is 256.
            case 'tile-size' as key:
                ensure_unique(key, entry)
                size = int(child.text)
                if size <= 0:
                    raise invalid_value_error(key, size)
                entry['tileSize'] = size

    for required_tag in REQUIRED_ENTRY_TAGS:
        if required_tag not in entry:
            raise RuntimeError(f'missing required tag "{required_tag}"')

    return entry


def main() -> None:
    response = requests.get('https://github.com/osmlab/editor-layer-index/raw/refs/heads/gh-pages/imagery.xml')

    with open('ignored_tiles_sources.json') as f:
        ignored_tiles_sources = json.load(f)

    entries = []
    i = 1
    for entry in ElementTree.fromstring(response.text):
        if tag_name(entry) != 'entry':
            continue
        try:
            entries.append(parse_entry(entry, ignored_tiles_sources))
        except Skip as e:
            print(f'Skipping entry #{i}:', e)
        except Exception as e:
            print(f'Error parsing entry #{i}:', e)
            print(traceback.format_exc())
        i += 1

    print(f'Entries: {i - 1} => {len(entries)}')

    with open('../js-sources/src/map/imagery_sources.json', mode='w', encoding='utf-8') as out:
        # noinspection PyTypeChecker
        json.dump(entries, out, indent=2)  # TODO remove indent when finished


if __name__ == '__main__':
    main()
