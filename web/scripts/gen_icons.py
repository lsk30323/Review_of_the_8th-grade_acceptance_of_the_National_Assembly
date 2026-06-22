#!/usr/bin/env python3
"""PWA 아이콘 생성기 (의존성 없음, 순수 파이썬 PNG 라이터).

브랜드 그라데이션 라운드 사각형 + 흰색 돋보기 글리프를 그린다.
4배 슈퍼샘플링으로 안티에일리어싱한다.

  python web/scripts/gen_icons.py

출력: web/public/icons/{icon-192,icon-512,icon-maskable-512}.png
"""
from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "public" / "icons"

PRIMARY = (31, 58, 138)   # #1f3a8a
ACCENT = (37, 99, 235)    # #2563eb
WHITE = (255, 255, 255)


def _lerp(a: float, b: float, t: float) -> float:
    """Lerp."""
    return a + (b - a) * t


def _dist_to_segment(px, py, ax, ay, bx, by):
    """Dist to segment."""
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    if seg2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def _sample(x, y, size, maskable):
    """슈퍼샘플 좌표(x,y)에서의 RGBA(0..1)를 반환."""
    # 라운드 사각형 마스크
    if maskable:
        inside_bg = True  # 풀블리드 (마스킹은 런처가 처리)
    else:
        r = size * 0.22
        qx = abs(x - size / 2) - (size / 2 - r)
        qy = abs(y - size / 2) - (size / 2 - r)
        qx = max(qx, 0.0)
        qy = max(qy, 0.0)
        inside_bg = math.hypot(qx, qy) <= r

    if not inside_bg:
        return (0.0, 0.0, 0.0, 0.0)

    # 대각선 그라데이션 배경
    t = (x + y) / (2 * size)
    bg = (
        _lerp(PRIMARY[0], ACCENT[0], t) / 255,
        _lerp(PRIMARY[1], ACCENT[1], t) / 255,
        _lerp(PRIMARY[2], ACCENT[2], t) / 255,
    )

    # 돋보기 글리프 (마스커블은 세이프 영역 안쪽으로 축소/중앙 이동)
    if maskable:
        cx, cy = size * 0.48, size * 0.46
        ring_r, ring_t = size * 0.16, size * 0.058
        handle_len, handle_hw = size * 0.18, size * 0.036
    else:
        cx, cy = size * 0.45, size * 0.43
        ring_r, ring_t = size * 0.20, size * 0.07
        handle_len, handle_hw = size * 0.24, size * 0.044

    d_center = math.hypot(x - cx, y - cy)
    on_ring = abs(d_center - ring_r) <= ring_t / 2

    ang = math.radians(45)
    p1x, p1y = cx + ring_r * math.cos(ang), cy + ring_r * math.sin(ang)
    p2x, p2y = p1x + handle_len * math.cos(ang), p1y + handle_len * math.sin(ang)
    on_handle = _dist_to_segment(x, y, p1x, p1y, p2x, p2y) <= handle_hw

    if on_ring or on_handle:
        return (WHITE[0] / 255, WHITE[1] / 255, WHITE[2] / 255, 1.0)
    return (bg[0], bg[1], bg[2], 1.0)


def render(size: int, maskable: bool, ss: int = 4) -> bytes:
    """Render."""
    rgba = bytearray(size * size * 4)
    inv = 1.0 / (ss * ss)
    for ty in range(size):
        for tx in range(size):
            r = g = b = a = 0.0
            for sy in range(ss):
                fy = ty + (sy + 0.5) / ss
                for sx in range(ss):
                    fx = tx + (sx + 0.5) / ss
                    sr, sg, sb, sa = _sample(fx, fy, size, maskable)
                    # 프리멀티플라이드 누적
                    r += sr * sa
                    g += sg * sa
                    b += sb * sa
                    a += sa
            a *= inv
            if a > 0:
                r = r * inv / a
                g = g * inv / a
                b = b * inv / a
            off = (ty * size + tx) * 4
            rgba[off] = max(0, min(255, round(r * 255)))
            rgba[off + 1] = max(0, min(255, round(g * 255)))
            rgba[off + 2] = max(0, min(255, round(b * 255)))
            rgba[off + 3] = max(0, min(255, round(a * 255)))
    return bytes(rgba)


def write_png(path: Path, size: int, rgba: bytes) -> None:
    """Write png."""
    def chunk(typ: bytes, data: bytes) -> bytes:
        """Chunk."""
        return (
            struct.pack(">I", len(data))
            + typ
            + data
            + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    stride = size * 4
    raw = bytearray()
    for y in range(size):
        raw.append(0)  # filter: none
        raw.extend(rgba[y * stride : (y + 1) * stride])
    idat = zlib.compress(bytes(raw), 9)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    )


def main() -> None:
    """Main."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = [
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-maskable-512.png", 512, True),
    ]
    for name, size, maskable in targets:
        rgba = render(size, maskable)
        write_png(OUT_DIR / name, size, rgba)
        print(f"wrote {name} ({size}x{size}, maskable={maskable})")


if __name__ == "__main__":
    main()
