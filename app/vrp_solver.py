from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import requests
import numpy as np


def create_distance_matrix(hub_location, order_locations):
    # Combine hub and order locations
    all_locations = [hub_location] + order_locations
    size = len(all_locations)

    # Calculate Euclidean distance between points
    distance_matrix = {}
    for from_node in range(size):
        distance_matrix[from_node] = {}
        for to_node in range(size):
            if from_node == to_node:
                distance_matrix[from_node][to_node] = 0
            else:
                distance_matrix[from_node][to_node] = int(
                    ((all_locations[from_node][0] - all_locations[to_node][0]) ** 2 +
                     (all_locations[from_node][1] - all_locations[to_node][1]) ** 2) ** 0.5 * 1000
                )
    return distance_matrix

def solve_vrp(distance_matrix, num_orders):
    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), 1, 0)

    # Create Routing Model
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        # Returns the distance between the two nodes.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Distance constraint
    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,  # no slack
        3000,  # vehicle maximum travel distance
        True,  # start cumul to zero
        dimension_name)
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    # Setting first solution heuristic
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        return None

    # Get the route for the vehicle
    route = []
    index = routing.Start(0)
    while not routing.IsEnd(index):
        route.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    route.append(manager.IndexToNode(index))
    return [route]

