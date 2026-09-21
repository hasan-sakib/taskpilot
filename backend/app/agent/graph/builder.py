from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.graph import routers
from app.agent.graph.deps import GraphDependencies
from app.agent.graph.state import AgentState
from app.agent.nodes import (
    completion_evaluation,
    final_report,
    goal_validation,
    permission_evaluation,
    plan_validation,
    planning,
    replanning,
    result_observation,
    result_verification,
    retry_recovery,
    task_selection,
    tool_execution,
)


def build_graph(deps: GraphDependencies) -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("goal_validation", goal_validation.make(deps))
    graph.add_node("planning", planning.make(deps))
    graph.add_node("plan_validation", plan_validation.make(deps))
    graph.add_node("task_selection", task_selection.make(deps))
    graph.add_node("permission_evaluation", permission_evaluation.make(deps))
    graph.add_node("tool_execution", tool_execution.make(deps))
    graph.add_node("result_observation", result_observation.make(deps))
    graph.add_node("result_verification", result_verification.make(deps))
    graph.add_node("retry_recovery", retry_recovery.make(deps))
    graph.add_node("replanning", replanning.make(deps))
    graph.add_node("completion_evaluation", completion_evaluation.make(deps))
    graph.add_node("final_report_generation", final_report.make(deps))

    graph.add_edge(START, "goal_validation")
    graph.add_conditional_edges("goal_validation", routers.route_goal_validation)
    graph.add_edge("planning", "plan_validation")
    graph.add_conditional_edges("plan_validation", routers.route_plan_validation)
    graph.add_conditional_edges("task_selection", routers.route_task_selection)
    graph.add_conditional_edges("permission_evaluation", routers.route_permission_evaluation)
    graph.add_edge("tool_execution", "result_observation")
    graph.add_edge("result_observation", "result_verification")
    graph.add_conditional_edges("result_verification", routers.route_result_verification)
    graph.add_conditional_edges("retry_recovery", routers.route_retry_recovery)
    graph.add_conditional_edges("completion_evaluation", routers.route_completion_evaluation)
    graph.add_conditional_edges("replanning", routers.route_replanning)
    graph.add_edge("final_report_generation", END)

    return graph


def compile_graph(deps: GraphDependencies, checkpointer) -> CompiledStateGraph:
    return build_graph(deps).compile(checkpointer=checkpointer)
