"""노드 위치 자동 재배치 — overlap 해소."""
from __future__ import annotations


def resolve_overlaps(
    positions: dict[str, tuple[float, float]],
    sizes: dict[str, tuple[float, float]],
    *,
    max_iter: int = 100,
    padding: float = 20.0,
) -> dict[str, tuple[float, float]]:
    """겹치는 노드 쌍을 반복적으로 밀어내 overlap 해소.

    각 iteration에서 모든 노드 쌍을 검사해 bbox 겹침 발견 시
    두 중심점을 잇는 방향으로 절반씩 밀어낸다.
    수렴 또는 max_iter 도달 시 종료.
    """
    pos = dict(positions)
    nodes = list(pos.keys())
    for _ in range(max_iter):
        moved = False
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = nodes[i], nodes[j]
                ax, ay = pos[a]
                bx, by = pos[b]
                aw, ah = sizes[a]
                bw, bh = sizes[b]
                dx = bx - ax
                dy = by - ay
                overlap_x = (aw + bw) / 2 + padding - abs(dx)
                overlap_y = (ah + bh) / 2 + padding - abs(dy)
                if overlap_x <= 0 or overlap_y <= 0:
                    continue
                if overlap_x < overlap_y:
                    shift = overlap_x / 2 + 1
                    sign = 1 if dx >= 0 else -1
                    pos[a] = (ax - sign * shift, ay)
                    pos[b] = (bx + sign * shift, by)
                else:
                    shift = overlap_y / 2 + 1
                    sign = 1 if dy >= 0 else -1
                    pos[a] = (ax, ay - sign * shift)
                    pos[b] = (bx, by + sign * shift)
                moved = True
        if not moved:
            break
    return pos
