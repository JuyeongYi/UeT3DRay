"""노드 위치 자동 재배치 — overlap 해소 + 위상 정렬."""
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


def hierarchical_arrange(graph) -> dict[str, tuple[float, float]]:
    """exec link 기반 위상적 layered layout.

    1. exec link → DAG (cycle 무시)
    2. BFS layer assignment (sources = column 0)
    3. 각 layer 내 부모 outgoing pin index median으로 정렬
    4. x = layer_idx * COL_WIDTH, y = position * ROW_HEIGHT
    """
    COL_WIDTH = 300.0
    ROW_HEIGHT = 150.0

    # exec output 핀 인덱스 맵: node → {pin_name: index}
    pin_index: dict[str, dict[str, int]] = {}
    for node in graph.nodes:
        out_pins = [p for p in node.pins if p.is_execution
                    and (p.direction or "").lower() in ("output", "io")]
        pin_index[node.name] = {p.name: i for i, p in enumerate(out_pins)}

    # exec link만 추출
    exec_edges: list[tuple[str, str]] = []
    for link in graph.links:
        parts = link.source_path.split(".", 1)
        if len(parts) < 2:
            continue
        s_node, s_rest = parts
        s_pin_top = s_rest.split(".", 1)[0]
        if s_node in pin_index and s_pin_top in pin_index[s_node]:
            t_node = link.target_path.split(".", 1)[0]
            exec_edges.append((s_node, t_node))

    # adjacency + in-degree
    children: dict[str, list[str]] = {}
    in_count: dict[str, int] = {}
    for s, t in exec_edges:
        children.setdefault(s, []).append(t)
        in_count[t] = in_count.get(t, 0) + 1

    all_nodes = [n.name for n in graph.nodes]
    sources = [n for n in all_nodes if in_count.get(n, 0) == 0]

    # BFS layer assignment — longest path
    layer: dict[str, int] = {}
    queue: list[tuple[str, int]] = [(s, 0) for s in sources]
    while queue:
        node, depth = queue.pop(0)
        if layer.get(node, -1) >= depth:
            continue
        layer[node] = depth
        for c in children.get(node, []):
            queue.append((c, depth + 1))

    # exec 연결 없는 isolated 노드 → 마지막 column
    max_layer = max(layer.values(), default=-1)
    for n in all_nodes:
        if n not in layer:
            max_layer += 1
            layer[n] = max_layer

    # 각 layer 내 정렬: 부모 outgoing pin index median
    layers_by_idx: dict[int, list[str]] = {}
    for n, l in layer.items():
        layers_by_idx.setdefault(l, []).append(n)

    def rank(node_name: str) -> float:
        indices = []
        for s, t in exec_edges:
            if t != node_name:
                continue
            for link in graph.links:
                if link.target_path.split(".", 1)[0] != node_name:
                    continue
                if link.source_path.split(".", 1)[0] != s:
                    continue
                s_pin = link.source_path.split(".", 1)[1].split(".", 1)[0]
                if s in pin_index and s_pin in pin_index[s]:
                    indices.append(pin_index[s][s_pin])
        return sum(indices) / len(indices) if indices else float("inf")

    positions: dict[str, tuple[float, float]] = {}
    for l_idx in sorted(layers_by_idx.keys()):
        layer_nodes = sorted(layers_by_idx[l_idx], key=lambda n: (rank(n), n))
        for row_idx, name in enumerate(layer_nodes):
            positions[name] = (l_idx * COL_WIDTH, row_idx * ROW_HEIGHT)
    return positions
