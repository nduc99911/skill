#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

# Import copywriter skill source
COPYWRITER_DIR = Path(__file__).resolve().parent.parent / "meta-ads-copywriter"
if str(COPYWRITER_DIR) not in sys.path:
    sys.path.append(str(COPYWRITER_DIR))

from copywriter import generate_ad_copy, generate_angles_struct  # noqa: E402


def build_matrix(campaign_name: str, angles_list: List[Dict[str, str]]) -> str:
    """Build markdown testing matrix from angle list."""
    formats = ["Video UGC", "Image", "Carousel"]

    header = (
        f"# Creative Testing Matrix - {campaign_name}\n\n"
        "| Creative ID | Angle | Hook | Format | Visual Concept | Funnel Stage |\n"
        "|---|---|---|---|---|---|"
    )

    lines = [header]
    idx = 1
    for angle in angles_list:
        angle_name = angle.get("angle", "-")
        hook = angle.get("hook", "-").replace("|", "\\|")

        for fmt in formats:
            creative_id = f"{campaign_name[:6].upper()}-{idx:03d}"
            if fmt == "Video UGC":
                visual = "Talking-head + screen recording thao tác tối ưu camp"
                stage = "TOF"
            elif fmt == "Image":
                visual = "Static quote + checklist 3 bước kiểm soát ngân sách"
                stage = "MOF"
            else:
                visual = "3 khung: vấn đề - quy trình - kết quả vận hành ổn định"
                stage = "BOF"

            lines.append(
                f"| {creative_id} | {angle_name} | {hook} | {fmt} | {visual} | {stage} |"
            )
            idx += 1

    return "\n".join(lines)


if __name__ == "__main__":
    # End-to-end Phase 4 test
    product_name = "Khóa học OpenClaw Thực chiến"
    insight_note = "Khách hàng là dân Ads mệt mỏi vì phải check camp thủ công mỗi ngày, sợ vít nhầm ngân sách"

    copy_md = generate_ad_copy(product_name, insight_note)
    angles = generate_angles_struct(product_name, insight_note)

    matrix_md = build_matrix("OpenClaw Creative Loop", angles)

    print(copy_md)
    print("\n" + "=" * 80 + "\n")
    print(matrix_md)
