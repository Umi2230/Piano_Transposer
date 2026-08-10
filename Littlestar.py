import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def mxl_to_musicxml(mxl_path, output_path):
    with zipfile.ZipFile(mxl_path, "r") as mxl_file:
        file_list = mxl_file.namelist()

        print("MXL 內的檔案：")
        for filename in file_list:
            print("-", filename)

        musicxml_filename = None

        # 方法一：從 container.xml 尋找樂譜位置
        if "META-INF/container.xml" in file_list:
            container_data = mxl_file.read("META-INF/container.xml")
            container_root = ET.fromstring(container_data)

            # 不限制 namespace，直接尋找 rootfile
            for element in container_root.iter():
                if element.tag.split("}")[-1] == "rootfile":
                    musicxml_filename = element.attrib.get("full-path")
                    if musicxml_filename:
                        break

        # 方法二：若 container.xml 找不到，就直接搜尋樂譜檔
        if musicxml_filename is None:
            candidates = [
                filename
                for filename in file_list
                if filename.lower().endswith((".musicxml", ".xml"))
                and filename != "META-INF/container.xml"
                and not filename.startswith("META-INF/")
            ]

            if not candidates:
                raise ValueError("MXL 裡找不到可用的 MusicXML 樂譜檔案")

            musicxml_filename = candidates[0]

        print(f"找到樂譜檔案：{musicxml_filename}")

        musicxml_data = mxl_file.read(musicxml_filename)

    Path(output_path).write_bytes(musicxml_data)
    print(f"轉換成功：{output_path}")


mxl_to_musicxml(
    "Little_Star2.mxl",
    "Little_Star2.musicxml"
)