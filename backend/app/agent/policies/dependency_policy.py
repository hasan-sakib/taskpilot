def has_cycle(edges: dict[str, list[str]]) -> bool:
    """Detect a cycle in a directed graph given as {node_id: [depends_on_ids]}.

    Shared by plan_validation (checking an LLM-generated plan before it's persisted)
    and the task.add_dependency tool (checking a single new edge against tasks already
    in the DB) -- same cycle-detection problem, two different sources of the edge map.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(edges, WHITE)

    def visit(node_id: str) -> bool:
        color[node_id] = GRAY
        for dep_id in edges.get(node_id, []):
            if dep_id not in color:
                continue
            if color[dep_id] == GRAY:
                return True
            if color[dep_id] == WHITE and visit(dep_id):
                return True
        color[node_id] = BLACK
        return False

    return any(color[node_id] == WHITE and visit(node_id) for node_id in edges)
