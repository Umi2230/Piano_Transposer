import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


# ==================== 使用者設定 ====================

INPUT_FILE = "Little_Star.mxl"
OUTPUT_FILE = "Little_Star_C_to_D.musicxml"

SOURCE_KEY = "C"
TARGET_KEY = "D"

# "shortest"：走最短距離；"up"：固定往上；"down"：固定往下
TRANSPOSE_DIRECTION = "shortest"


# ==================== 音樂資料 ====================

STEP_TO_NUMBER = {
    "C": 0,
    "D": 2,
    "E": 4,
    "F": 5,
    "G": 7,
    "A": 9,
    "B": 11,
}

# 各調主音在 12 半音中的位置
KEY_TO_NUMBER = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
    "Cb": 11,
}

# MusicXML <fifths> 的值：正數是升記號數量，負數是降記號數量
KEY_TO_FIFTHS = {
    "Cb": -7,
    "Gb": -6,
    "Db": -5,
    "Ab": -4,
    "Eb": -3,
    "Bb": -2,
    "F": -1,
    "C": 0,
    "G": 1,
    "D": 2,
    "A": 3,
    "E": 4,
    "B": 5,
    "F#": 6,
    "C#": 7,
}

# 移調後若使用升記號時的拼法
SHARP_PITCHES = [
    ("C", 0),
    ("C", 1),
    ("D", 0),
    ("D", 1),
    ("E", 0),
    ("F", 0),
    ("F", 1),
    ("G", 0),
    ("G", 1),
    ("A", 0),
    ("A", 1),
    ("B", 0),
]

# 移調後若使用降記號時的拼法
FLAT_PITCHES = [
    ("C", 0),
    ("D", -1),
    ("D", 0),
    ("E", -1),
    ("E", 0),
    ("F", 0),
    ("G", -1),
    ("G", 0),
    ("A", -1),
    ("A", 0),
    ("B", -1),
    ("B", 0),
]


# ==================== 輔助函式 ====================

def normalize_key_name(key_name):
    """把 C Major、Bb Major、F♯ 等寫法整理成 C、Bb、F#。"""
    key_name = key_name.strip()
    key_name = key_name.replace("Major", "").replace("major", "")
    key_name = key_name.replace("大調", "").replace("♯", "#").replace("♭", "b")
    key_name = key_name.replace(" ", "")

    if not key_name:
        raise ValueError("Key 不可以是空白")

    return key_name[0].upper() + key_name[1:]


def calculate_semitones(source_key, target_key, direction="shortest"):
    """計算原 Key 到目標 Key 的半音差。"""
    source_key = normalize_key_name(source_key)
    target_key = normalize_key_name(target_key)

    if source_key not in KEY_TO_NUMBER:
        raise ValueError(f"不支援原 Key：{source_key}")
    if target_key not in KEY_TO_NUMBER:
        raise ValueError(f"不支援目標 Key：{target_key}")

    upward = (KEY_TO_NUMBER[target_key] - KEY_TO_NUMBER[source_key]) % 12

    if direction == "up":
        return upward
    if direction == "down":
        return upward - 12 if upward != 0 else 0
    if direction == "shortest":
        return upward - 12 if upward > 6 else upward

    raise ValueError("TRANSPOSE_DIRECTION 只能是 shortest、up 或 down")


def local_name(element):
    """去掉 XML namespace，只留下 note、pitch 等標籤名稱。"""
    return element.tag.split("}")[-1]


def find_child(element, tag_name):
    """尋找元素的直接子元素，並相容有 namespace 的 MusicXML。"""
    for child in element:
        if local_name(child) == tag_name:
            return child
    return None


def make_child_tag(parent, tag_name):
    """建立和父元素使用相同 namespace 的新標籤。"""
    if parent.tag.startswith("{"):
        namespace = parent.tag.split("}")[0] + "}"
        return namespace + tag_name
    return tag_name


def pitch_to_number(step, alter, octave):
    """例如 C4 -> 60、C#4 -> 61、Db4 -> 61。"""
    return (octave + 1) * 12 + STEP_TO_NUMBER[step] + alter


def number_to_pitch(pitch_number, use_flats=False):
    """把絕對半音編號轉回 step、alter、octave。"""
    pitch_class = pitch_number % 12
    octave = pitch_number // 12 - 1
    pitch_table = FLAT_PITCHES if use_flats else SHARP_PITCHES
    step, alter = pitch_table[pitch_class]
    return step, alter, octave


def format_note(step, alter, octave):
    """把 MusicXML 音高整理成 C#4、Bb3 等顯示文字。"""
    accidental = ""
    if alter > 0:
        accidental = "#" * alter
    elif alter < 0:
        accidental = "b" * abs(alter)
    return f"{step}{accidental}{octave}"


def load_musicxml(input_file):
    """讀取一般 .musicxml/.xml，或從壓縮的 .mxl 中取出樂譜。"""
    input_path = Path(input_file)

    if not input_path.exists():
        raise FileNotFoundError(f"找不到輸入檔案：{input_file}")

    if input_path.suffix.lower() != ".mxl":
        return input_path.read_bytes(), input_path.name

    with zipfile.ZipFile(input_path, "r") as mxl:
        score_file = None

        # 優先依照 .mxl 的 container.xml 找真正的樂譜檔案
        try:
            container_data = mxl.read("META-INF/container.xml")
            container_root = ET.fromstring(container_data)
            for element in container_root.iter():
                if local_name(element) == "rootfile":
                    score_file = element.get("full-path")
                    if score_file:
                        break
        except KeyError:
            pass

        # 若沒有 container.xml，再從壓縮檔中尋找 MusicXML
        if score_file is None:
            candidates = [
                name
                for name in mxl.namelist()
                if name.lower().endswith((".xml", ".musicxml"))
                and not name.startswith("META-INF/")
            ]
            if not candidates:
                raise FileNotFoundError(".mxl 裡找不到 MusicXML 樂譜檔")
            score_file = candidates[0]

        return mxl.read(score_file), score_file


def update_key_signature(root, target_key):
    """把 MusicXML 的 <fifths> 更新成目標大調的調號。"""
    target_key = normalize_key_name(target_key)
    if target_key not in KEY_TO_FIFTHS:
        print(f"⚠️ 找不到 {target_key} Major 的調號資料，略過 <fifths> 更新")
        return 0

    updated_count = 0
    for element in root.iter():
        if local_name(element) == "fifths":
            element.text = str(KEY_TO_FIFTHS[target_key])
            updated_count += 1
    return updated_count


def transpose_score(root, semitones, target_key):
    """修改所有有 <pitch> 的 note，並回傳實際移調的音符數。"""
    target_key = normalize_key_name(target_key)
    use_flats = KEY_TO_FIFTHS.get(target_key, 0) < 0
    transposed_count = 0

    for note in root.iter():
        if local_name(note) != "note":
            continue

        # 休止符及打擊樂的 unpitched note 沒有一般音高，不需要移調
        if find_child(note, "rest") is not None:
            continue

        pitch = find_child(note, "pitch")
        if pitch is None:
            continue

        step_element = find_child(pitch, "step")
        alter_element = find_child(pitch, "alter")
        octave_element = find_child(pitch, "octave")

        if step_element is None or octave_element is None:
            continue

        old_step = step_element.text
        old_alter = int(float(alter_element.text)) if alter_element is not None else 0
        old_octave = int(octave_element.text)

        old_number = pitch_to_number(old_step, old_alter, old_octave)
        new_number = old_number + semitones
        new_step, new_alter, new_octave = number_to_pitch(new_number, use_flats)

        # 真正將計算結果寫回 MusicXML
        step_element.text = new_step
        octave_element.text = str(new_octave)

        if new_alter == 0:
            if alter_element is not None:
                pitch.remove(alter_element)
        else:
            if alter_element is None:
                alter_element = ET.Element(make_child_tag(pitch, "alter"))
                pitch.insert(1, alter_element)
            alter_element.text = str(new_alter)

        # 移除舊的顯示用 accidental，讓樂譜軟體依新調號重新排版
        accidental_element = find_child(note, "accidental")
        if accidental_element is not None:
            note.remove(accidental_element)

        old_name = format_note(old_step, old_alter, old_octave)
        new_name = format_note(new_step, new_alter, new_octave)
        print(f"{old_name:5} → {new_name}")
        transposed_count += 1

    return transposed_count


def run_algorithm_tests():
    """測試升降記號、降記號及跨八度。"""
    assert number_to_pitch(pitch_to_number("C", 0, 4) + 2) == ("D", 0, 4)
    assert number_to_pitch(pitch_to_number("B", 0, 4) + 2) == ("C", 1, 5)
    assert number_to_pitch(pitch_to_number("B", -1, 3) + 2) == ("C", 0, 4)
    assert number_to_pitch(pitch_to_number("E", 0, 4) - 2) == ("D", 0, 4)
    print("✅ 演算法測試通過：一般音、升降記號、降記號、跨八度")


def main():
    source_key = normalize_key_name(SOURCE_KEY)
    target_key = normalize_key_name(TARGET_KEY)
    semitones = calculate_semitones(source_key, target_key, TRANSPOSE_DIRECTION)

    run_algorithm_tests()
    print(f"找到設定：{source_key} Major → {target_key} Major")
    print(f"半音差：{semitones:+d}\n")

    xml_data, score_file = load_musicxml(INPUT_FILE)
    print(f"找到樂譜：{score_file}\n")

    root = ET.fromstring(xml_data)
    note_count = transpose_score(root, semitones, target_key)
    key_count = update_key_signature(root, target_key)

    tree = ET.ElementTree(root)
    try:
        ET.indent(tree, space="  ")
    except AttributeError:
        # Python 3.8 以下沒有 ET.indent，但仍可正常輸出
        pass

    tree.write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)

    output_path = Path(OUTPUT_FILE)
    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"\n✅ 共移調 {note_count} 個有音高的 note")
        print(f"✅ 更新 {key_count} 個 <fifths> 調號")
        print(f"✅ 移調完成：{OUTPUT_FILE}")
        print(f"✅ 檔案大小：{output_path.stat().st_size} bytes")
    else:
        raise OSError("輸出檔案建立失敗")


if __name__ == "__main__":
    main()
