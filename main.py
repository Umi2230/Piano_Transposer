import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


# 要處理的鋼琴譜
mxl_file = "Little_Star.mxl"

# 輸出檔案
output_file = "Little_Star_transposed.musicxml"

# 正數是升，負數是降
transpose_semitones = 2


# 每個基本音與 C 相差的半音數
STEP_TO_NUMBER = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11
}


# 移調後的音名，目前黑鍵統一用升記號
NUMBER_TO_PITCH = [
    ("C", 0),   # C
    ("C", 1),   # C#
    ("D", 0),   # D
    ("D", 1),   # D#
    ("E", 0),   # E
    ("F", 0),   # F
    ("F", 1),   # F#
    ("G", 0),   # G
    ("G", 1),   # G#
    ("A", 0),   # A
    ("A", 1),   # A#
    ("B", 0)    # B
]


# 1. 打開 .mxl
with zipfile.ZipFile(mxl_file, "r") as mxl:

    xml_files = [
        name for name in mxl.namelist()
        if name.lower().endswith((".xml", ".musicxml"))
        and not name.startswith("META-INF/")
    ]

    if not xml_files:
        raise FileNotFoundError("找不到 MusicXML 樂譜檔")

    score_file = xml_files[0]
    print("找到樂譜：", score_file)

    xml_data = mxl.read(score_file)


# 2. 解析 XML
root = ET.fromstring(xml_data)


# 3. 找出所有音符
notes = root.findall(".//note")

print(f"共找到 {len(notes)} 個 note")
print(f"\n開始移調：{transpose_semitones:+d} 個半音\n")


# 4. 逐一移調音符
for note in notes:

    # 跳過休止符
    if note.find("rest") is not None:
        continue

    pitch = note.find("pitch")

    if pitch is None:
        continue

    step = pitch.find("step")
    alter = pitch.find("alter")
    octave = pitch.find("octave")

    if step is None or octave is None:
        continue

    # 儲存原始音高
    old_step = step.text
    old_octave = int(octave.text)

    if alter is None:
        old_alter = 0
    else:
        old_alter = int(float(alter.text))

    # 原始音符轉為絕對半音編號
    old_pitch_number = (
        (old_octave + 1) * 12
        + STEP_TO_NUMBER[old_step]
        + old_alter
    )

    # 升高或降低指定半音
    new_pitch_number = old_pitch_number + transpose_semitones

    # 算出新音名和新八度
    pitch_class = new_pitch_number % 12
    new_octave = new_pitch_number // 12 - 1
    new_step, new_alter = NUMBER_TO_PITCH[pitch_class]

    # 修改 XML 中的音名與八度
    step.text = new_step
    octave.text = str(new_octave)

    # 修改 XML 中的升降記號
    if new_alter == 0:
        if alter is not None:
            pitch.remove(alter)
    else:
        if alter is None:
            alter = ET.Element("alter")
            pitch.insert(1, alter)

        alter.text = str(new_alter)

    # 組合原始音符名稱
    old_name = old_step

    if old_alter == 1:
        old_name += "#"
    elif old_alter == -1:
        old_name += "b"

    old_name += str(old_octave)

    # 組合移調後音符名稱
    new_name = new_step

    if new_alter == 1:
        new_name += "#"

    new_name += str(new_octave)

    print(f"{old_name} → {new_name}")


# 5. 輸出新的 MusicXML
tree = ET.ElementTree(root)

tree.write(
    output_file,
    encoding="utf-8",
    xml_declaration=True
)


# 6. 確認輸出是否成功
output_path = Path(output_file)

if output_path.exists() and output_path.stat().st_size > 0:
    print(f"\n✅ 移調完成：{output_file}")
    print(f"✅ 檔案大小：{output_path.stat().st_size} bytes")
else:
    print("\n❌ 輸出失敗")