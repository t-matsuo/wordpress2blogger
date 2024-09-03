#!/usr/bin/env python

import os
import sys
import xml.etree.ElementTree as ET
import re
import datetime
import argparse
import logging
from pydantic import BaseModel


class Args(BaseModel):
    input_file: str
    output_file: str = "blogger_posts.xml"
    blogger_id: str = "0000000000000000000"
    blogger_url: str = "http://xxxx.blogspot.com/"
    blogger_author: str = "admin"
    blogger_email: str = "noreply@blogger.com"
    read_pages: int = 0
    skip_pages: int = 0


class Wordpress2Blogger:
    def __init__(self, args, *, logger=None):
        if logger != None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.INFO)
        self.args = args
        self.check_args()

    def check_args(self):
        args = self.args
        # check wordpress xml file
        if os.path.isfile(args.input_file) == False:
            raise Exception(args.input_file + " file not found")
        # check int
        if args.read_pages < 0:
            raise Exception("read_pages needs 0(default) or positive number")
        if args.skip_pages < 0:
            raise Exception("skip_pages needs 0(default) or positive number")

    def convert(self):
        args = self.args
        wp_tree = ET.parse(args.input_file)
        wp_root = wp_tree.getroot()

        # XML Namespaces
        ns = {
            "excerpt": "http://wordpress.org/export/1.2/excerpt/",
            "content": "http://purl.org/rss/1.0/modules/content/",
            "wfw": "http://wellformedweb.org/CommentAPI/",
            "dc": "http://purl.org/dc/elements/1.1/",
            "wp": "http://wordpress.org/export/1.2/",
            "xmlns": "http://www.w3.org/2005/Atom",
        }

        # create blogger xml ElementTree
        blogger_feed = ET.Element("feed")
        blogger_tree = ET.ElementTree(blogger_feed)

        # create blogger feed attributes
        blogger_feed.set("xmlns", "http://www.w3.org/2005/Atom")
        blogger_feed.set("xmlns:openSearch", "http://a9.com/-/spec/opensearchrss/1.0/")
        blogger_feed.set("xmlns:gd", "http://schemas.google.com/g/2005")
        blogger_feed.set("xmlns:thr", "http://purl.org/syndication/thread/1.0")
        blogger_feed.set("xmlns:georss", "http://www.georss.org/georss")

        # create blogger subelements
        feed_id = ET.SubElement(blogger_feed, "id")
        feed_id.text = "tag:blogger.com,1999:blog-" + args.blogger_id + ".archive"

        feed_link1 = ET.SubElement(blogger_feed, "link")
        feed_link1.set("rel", "http://schemas.google.com/g/2005#feed")
        feed_link1.set("type", "application/atom+xml")
        feed_link1.set(
            "href", "https://www.blogger.com/feeds/" + args.blogger_id + "/archive"
        )

        feed_link2 = ET.SubElement(blogger_feed, "link")
        feed_link2.set("rel", "self")
        feed_link2.set("type", "application/atom+xml")
        feed_link2.set(
            "href", "https://www.blogger.com/feeds/" + args.blogger_id + "/archive"
        )

        feed_link3 = ET.SubElement(blogger_feed, "link")
        feed_link3.set("rel", "http://schemas.google.com/g/2005#post")
        feed_link3.set("type", "application/atom+xml")
        feed_link3.set(
            "href", "https://www.blogger.com/feeds/" + args.blogger_id + "/archive"
        )

        feed_link4 = ET.SubElement(blogger_feed, "link")
        feed_link4.set("rel", "alternate")
        feed_link4.set("type", "text/html")
        feed_link4.set("href", args.blogger_url)

        feed_generator = ET.SubElement(blogger_feed, "generator")
        feed_generator.set("version", "7.00")
        feed_generator.set("uri", "https://www.blogger.com")
        feed_generator.text = "Blogger"

        feed_author_element = ET.SubElement(blogger_feed, "author")
        feed_author_name_element = ET.SubElement(feed_author_element, "name")
        feed_author_name_element.text = args.blogger_author
        feed_author_email_element = ET.SubElement(feed_author_element, "email")
        feed_author_email_element.text = args.blogger_email

        feed_author_gdimage_element = ET.SubElement(feed_author_element, "gd:image")
        feed_author_gdimage_element.set(
            "rel", "http://schemas.google.com/g/2005#thumbnail"
        )
        feed_author_gdimage_element.set("width", "35")
        feed_author_gdimage_element.set("height", "35")
        feed_author_gdimage_element.set(
            "src", "//www.blogger.com/img/blogger_logo_round_35.png"
        )

        # initial post_id
        post_id = 1
        # skip count
        skip_count = 0
        # read count
        read_count = 0

        # handling wordpress all items
        for item in wp_root.findall("./channel/item"):

            # Reading Wordpress xml  ###############################################
            # skip attachment file item
            wp_post_type = item.find("wp:post_type", ns).text
            if wp_post_type != ("post"):
                continue

            # wordpress item title
            wp_title = item.find("title").text.strip()

            # skip reading
            if skip_count < args.skip_pages:
                self.logger.info("Skip: Post No." + str(post_id) + " title=" + wp_title)
                skip_count += 1
                post_id += 1
                continue
            else:
                self.logger.info("Read: Post No." + str(post_id) + " title=" + wp_title)

            self.logger.debug("post_type=" + wp_post_type)
            # wordpress item URL
            wp_post_url = item.find("link").text.strip()
            wp_post_url_path = re.sub(r"^http.*//.*?/", "", wp_post_url)
            self.logger.debug("link(wp_post_url)=" + wp_post_url)
            self.logger.debug("link(wp_post_url_path)=" + wp_post_url_path)

            # wordpress post date
            wp_post_date_gmt = item.find("wp:post_date_gmt", ns).text
            self.logger.debug("wp_post_date_gmt=" + wp_post_date_gmt)
            wp_post_date_gmt_formatted = datetime.datetime.strptime(
                wp_post_date_gmt, "%Y-%m-%d %H:%M:%S"
            )
            self.logger.debug(
                "wp_post_date_gmt_formatted="
                + wp_post_date_gmt_formatted.strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            wp_post_date_gmt = wp_post_date_gmt_formatted.strftime("%Y-%m-%dT%H:%M:%SZ")

            # wordpress modified date
            wp_post_modified_gmt = item.find("wp:post_modified_gmt", ns).text
            self.logger.debug("wp_post_modified_gmt=" + wp_post_modified_gmt)
            wp_post_modified_gmt_formatted = datetime.datetime.strptime(
                wp_post_modified_gmt, "%Y-%m-%d %H:%M:%S"
            )
            self.logger.debug(
                "wp_post_modified_gmt_formatted="
                + wp_post_modified_gmt_formatted.strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            wp_post_modified_gmt = wp_post_modified_gmt_formatted.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            # wordpress categories
            categories = item.findall("category")
            for category in categories:
                self.logger.debug("category=" + category.text)

            # wordpress content
            wp_content = item.find("content:encoded", ns).text
            wp_content_lines = wp_content.splitlines()
            for line in wp_content_lines:
                self.logger.debug("wp_content: " + line)

            # constructing blogger xml file #####################################
            post_id_str = str(post_id).zfill(19)

            # blogger entry
            entry = ET.SubElement(blogger_feed, "entry")
            # ID
            id_element = ET.SubElement(entry, "id")
            id_element.text = (
                "tag:blogger.com,1999:blog-"
                + args.blogger_id
                + ".post-"
                + str(post_id_str)
            )

            # blogger title
            title_element = ET.SubElement(entry, "title")
            title_element.text = wp_title
            title_element.set("type", "text")

            # blogger published date
            published_element = ET.SubElement(entry, "published")
            published_element.text = wp_post_date_gmt

            # blogger updated date
            updated_element = ET.SubElement(entry, "updated")
            updated_element.text = wp_post_modified_gmt

            # blogger auther
            author_element = ET.SubElement(entry, "author")
            author_name_element = ET.SubElement(author_element, "name")
            author_name_element.text = args.blogger_author
            author_email_element = ET.SubElement(author_element, "email")
            author_email_element.text = args.blogger_email
            author_gdimage_element = ET.SubElement(author_element, "gd:image")
            author_gdimage_element.set(
                "rel", "http://schemas.google.com/g/2005#thumbnail"
            )
            author_gdimage_element.set("width", "35")
            author_gdimage_element.set("height", "35")
            author_gdimage_element.set(
                "src", "//www.blogger.com/img/blogger_logo_round_35.png"
            )

            # blogger link edit
            link_edit = ET.SubElement(entry, "link")
            link_edit.set("rel", "edit")
            link_edit.set("type", "application/atom+xml")
            link_edit.set(
                "href",
                args.blogger_url + "feeds/" + args.blogger_id + "/" + post_id_str,
            )

            # blogger link self
            link_self = ET.SubElement(entry, "link")
            link_self.set("rel", "self")
            link_self.set("type", "application/atom+xml")
            link_self.set(
                "href",
                args.blogger_url + "feeds/" + args.blogger_id + "/" + post_id_str,
            )

            # blogger url
            link_alternate = ET.SubElement(entry, "link")
            link_alternate.set("rel", "alternate")
            link_alternate.set("type", "text/html")
            link_alternate.set("href", args.blogger_url + wp_post_url_path)
            link_alternate.set("title", wp_title)

            # blogger categories
            category_default_element = ET.SubElement(entry, "category")
            category_default_element.set(
                "scheme", "http://schemas.google.com/g/2005#kind"
            )
            category_default_element.set(
                "term", "http://schemas.google.com/blogger/2008/kind#post"
            )
            for category in categories:
                cat_tmp = ET.SubElement(entry, "category")
                cat_tmp.set("scheme", "http://www.blogger.com/atom/ns#")
                cat_tmp.set("term", category.text)

            # blogger content
            content_element = ET.SubElement(entry, "content")
            content_element.set("type", "html")
            content_element.text = self.handle_content(wp_content)

            # insert new lines into xml
            ET.indent(blogger_feed, space="  ")

            post_id += 1
            read_count += 1

            if args.read_pages != 0:
                if read_count == args.read_pages:
                    break

        # writing blogger xml file
        blogger_tree.write(
            self.args.output_file, encoding="utf-8", xml_declaration=True
        )

    # TODO: convert image url, wordpress css and so on
    def handle_content(self, content):
        images = set(re.findall(r"(http|https)(://.*?\.)(jpg|jpeg|png)", content))
        for image in images:
            image_url = "".join(image)
            self.logger.debug("image_url=" + image_url)

        return content


# NOTE: logging level
# 50 CRITICAL
# 40 ERROR
# 30 WARNING
# 20 INFO
# 10 DEBUG
#  0 NOTSET
def init_logging(logger: logging.Logger, debug: bool):
    # Supress stdout if loglevel > info
    def level_filter(record):
        return record.levelno <= logging.INFO

    formatter = logging.Formatter(
        "{asctime} {name:<8s} {levelname:<8s} {message}", style="{"
    )
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(level_filter)

    # create stderr stream
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)

    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    return logger


def parse_args(*, logger=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", help="exported xml file from wordpress")
    parser.add_argument(
        "--blogger_id",
        type=str,
        default="0000000000000000000",
        help="your blogger ID",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="blogger_posts.xml",
        help="output xml filename. default is blogger_posts.xml",
    )
    parser.add_argument(
        "--blogger_url",
        type=str,
        default="http://xxxx.blogspot.com/",
        help="your blogger URL. default is 'http://xxxx.blogspot.com/'",
    )
    parser.add_argument(
        "--blogger_author",
        type=str,
        default="admin",
        help="your blogger author name. default is 'admin'",
    )
    parser.add_argument(
        "--blogger_email",
        type=str,
        default="noreply@blogger.com",
        help="your blogger author email. default is 'noreply@blogger.com'",
    )
    parser.add_argument(
        "--read_pages",
        type=int,
        default=0,
        help="read number of wordpress posts. default is '0' which means read all posts",
    )
    parser.add_argument(
        "--skip_pages",
        type=int,
        default=0,
        help="skip reading number of wordpress posts. default is '0'(no skip).",
    )
    parser.add_argument(
        "--debug",
        help="verbose message.",
        action="store_true",
    )
    args = parser.parse_args()
    if args.debug:
        print("args:" + str(args) + "\n")

    args_data = {
        "input_file": args.input_file,
        "output_file": args.output_file,
        "blogger_url": args.blogger_url,
        "blogger_author": args.blogger_author,
        "blogger_email": args.blogger_email,
        "read_pages": args.read_pages,
        "skip_pages": args.skip_pages,
    }
    return Args(**args_data), args.debug


if __name__ == "__main__":
    args, debug = parse_args()
    main_logger = init_logging(logging.getLogger(__name__), debug)
    w2b = Wordpress2Blogger(args, logger=main_logger)
    w2b.convert()
