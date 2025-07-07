"""
Given data structure returned by collect submodule, creates human-readable reports.
"""

from __future__ import annotations

import logging
from xml.etree.ElementTree import Element, SubElement, tostring

from pycodetags.data_tags.data_tags_classes import DATA

logger = logging.getLogger(__name__)


def print_rss(found: list[DATA], channel_info: dict[str, str]) -> None:
    """
    Prints TODOs and Dones in a structured RSS 2.0 format.

    Args:
        found (list[DATA]): The collected TODOs and Dones.
        channel_info (dict[str, str]): Information about the RSS channel.
    """
    rss = Element("rss", version="2.0", attrib={"xmlns:atom": "http://www.w3.org/2005/Atom"})
    channel = SubElement(rss, "channel")

    title = SubElement(channel, "title")
    title.text = channel_info.get("title", "Code Tags RSS Feed")

    link = SubElement(channel, "link")
    link.text = channel_info.get("link", "")

    description = SubElement(channel, "description")
    description.text = channel_info.get("description", "An RSS feed of code tags.")

    for item_data in found:
        item = SubElement(channel, "item")

        item_title = SubElement(item, "title")
        item_title.text = item_data.comment or "No comment"

        item_link = SubElement(item, "link")
        item_link.text = item_data.terminal_link()

        item_description = SubElement(item, "description")
        item_description.text = item_data.as_data_comment()

        # Attempt to find a publication date
        pub_date = None
        if item_data.data_fields:
            # Common date fields, add more if needed
            for date_field in ["origination_date", "date", "created"]:
                if date_field in item_data.data_fields:
                    pub_date = item_data.data_fields[date_field]
                    break
        if pub_date:
            item_pub_date = SubElement(item, "pubDate")
            item_pub_date.text = str(pub_date)

        guid = SubElement(item, "guid", isPermaLink="false")
        start_line, start_char, end_line, end_char = item_data.offsets
        guid.text = f"{item_data.file_path}-{start_line}-{item_data.comment}"

    # Pretty print the XML
    from xml.dom import minidom

    xml_str = tostring(rss, "utf-8")
    parsed_str = minidom.parseString(xml_str)
    print(parsed_str.toprettyxml(indent="  "))
