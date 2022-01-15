import os
import xml.etree.ElementTree as ET
from PIL import Image
from xml_manipulation import *
from tools import get_filelist, get_xml_bbox_area
import argparse


def get_small_bbox_list(area_thresh, XML_PATH):
    """
    Get a list of image filenames where the largest bounding box area of the image is lesser than the threshold passed.

    Arguments:
        area_thresh: int, bounding box area smaller than this threshold will be removed
        XML_PATH: path, XML annotation folder path

    Returns:
        imglist: list, a list contains image filenames

    """

    # extract all file in XML folder
    filenames = get_filelist(XML_PATH)
    # empty lists in action
    imglist = []
    for item in filenames:
        xml_path = os.path.join(XML_PATH, f"{item}.xml")
        tree = ET.parse(xml_path)
        root = tree.getroot()
        areas = get_xml_bbox_area(root)
        if max(areas) <= area_thresh:
            imglist.append(item)
    return imglist


def drop_crop_small_bbox(
    area_thresh,
    IMG_PATH,
    XML_PATH,
    OUTPUT_IMG_PATH="crop_sbbox_img",
    OUTPUT_XML_PATH="crop_sbbox_xml",
):
    """
    For image with extremely small bounding boxes, this function can be used to drop them (bounding boxes area < area_thresh) and crop out the remaining part of the image.

    Arguments:
        area_thresh: int, bounding box area smaller than this threshold will be removed
        IMG_PATH: path, image folder path
        XML_PATH: path, XML annotation folder path
        OUTPUT_IMG_PATH: str, default="crop_sbbox_img", folder name to save cropped image
        OUTPUT_ANN_PATH: str, default="crop_sbbox_xml", folder name to save cropped XML annotation

    Returns:
        None

    """

    # extract all file in XML folder
    filenames = get_filelist(XML_PATH)
    for item in filenames:
        # empty lists in action
        x_val = []
        y_val = []
        small_bboxes = []

        # xml tree
        xml_path = os.path.join(XML_PATH, f"{item}.xml")
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # extract bboxes and respective area in XML file
        bboxes = get_xml_bbox(root)
        area = get_xml_bbox_area(root)

        # index of bboxes with area > area_thresh
        index_list = [area.index(int(f"{i}")) for i in area if i > area_thresh]
        for index in index_list:
            target_box = bboxes[index]
            x_val.append(target_box[0])
            y_val.append(target_box[1])
            x_val.append(target_box[2])
            y_val.append(target_box[3])

        # crop image excluding the small bboxes (area < area_thresh)!
        left, right = min(x_val), max(x_val)
        top, bottom = min(y_val), max(y_val)

        # index of bboxes with area < area_thresh
        small_index_list = [area.index(int(f"{i}")) for i in area if i < area_thresh]
        for index in small_index_list:
            s_target_box = bboxes[index]
            small_bboxes.append(s_target_box)

        print(
            f"\nImage {item} initial cropping coordinates: {[left, top, right, bottom]}"
        )
        print(f"Count of small bounding box : {len(small_bboxes)}")

        # inspect which bounding boxes to keep/ to drop
        to_keep = []
        for obj in small_bboxes:
            txmin, tymin, txmax, tymax = obj[0], obj[1], obj[2], obj[3]
            # condition: keep small bbox coordinates within/ intersect with cropping region
            if not (
                (txmin < left and txmax < left)
                or (txmin > right and txmax > right)
                or (tymin < top and tymax < top)
                or (tymin > bottom and tymax > bottom)
            ):
                to_keep.append(obj)

        # adjust the final cropping coordinates
        for obj in to_keep:
            txmin, tymin, txmax, tymax = obj[0], obj[1], obj[2], obj[3]
            if txmin < left:
                left = txmin
            elif tymin < top:
                top = tymin
            elif txmax > right:
                right = txmax
            elif tymax > bottom:
                bottom = tymax

        print(
            f"Image {item} finalized cropping coordinates: {[left, top, right, bottom]}"
        )

        # load and crop image
        im = Image.open(os.path.join(IMG_PATH, f"{item}.jpg"))
        imc = im.crop((left, top, right, bottom))
        w, h = imc.size
        # save cropped image
        save_img_folder = os.path.join(OUTPUT_IMG_PATH)
        os.makedirs(save_img_folder, exist_ok=True)
        imc.save(os.path.join(OUTPUT_IMG_PATH, f"{item}.jpg"))

        # drop finalized small bounding boxes in XML
        drop_xml_small_bbox(root, area_thresh, to_keep)
        update_crop_xml_bbox(root, w, h, left, top)
        # save cropped XML
        save_xml_folder = os.path.join(OUTPUT_XML_PATH)
        os.makedirs(save_xml_folder, exist_ok=True)
        tree.write(os.path.join(OUTPUT_XML_PATH, f"{item}.xml"))

    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--area", type=int, required=True, help="maximum area threshold to crop"
    )
    parser.add_argument(
        "--imgpath",
        type=str,
        required=True,
        help="path to image dataset folder",
    )
    parser.add_argument(
        "--xmlpath",
        type=str,
        required=True,
        help="path to XML annotations folder",
    )
    parser.add_argument(
        "--n_imgpath",
        type=str,
        default="crop_sbbox_img",
        help="path to save cropped images",
    )
    parser.add_argument(
        "--n_xmlpath",
        type=str,
        default="crop_sbbox_xml",
        help="path to save cropped XML annotations",
    )

    args = parser.parse_args()

    drop_crop_small_bbox(
        area_thresh=args.area,
        IMG_PATH=args.imgpath,
        XML_PATH=args.xmlpath,
        OUTPUT_IMG_PATH=args.n_imgpath,
        OUTPUT_XML_PATH=args.n_xmlpath,
    )
