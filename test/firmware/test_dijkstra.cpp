#include <Arduino.h>
#include <unity.h>
#include "routing.h"
#include "link_state.h"
#include "graph_topology.h"

static BuildingGraph test_graph;
static LinkStateTable ls_table;

static void build_linear_graph(void) {
    test_graph.node_count = 3;
    test_graph.edge_count = 2;
    test_graph.nodes[0] = {1, 0, 0, 0, true, 25.0f, 80.0f, 0.0f, 1000.0f, 10.0f};
    test_graph.nodes[1] = {2, 0, 10, 0, false, 25.0f, 80.0f, 0.0f, 1000.0f, 8.0f};
    test_graph.nodes[2] = {3, 0, 20, 0, false, 25.0f, 80.0f, 0.0f, 1000.0f, 8.0f};
    test_graph.edges[0] = {1, 2, 10.0f, 5, false};
    test_graph.edges[1] = {2, 3, 10.0f, 5, false};

    link_state_init(&ls_table);
    link_state_upsert(&ls_table, 1, 0, 0, 0.0f, 25.0f, 0.0f, false);
    link_state_upsert(&ls_table, 2, 0, 0, 0.0f, 25.0f, 0.0f, false);
    link_state_upsert(&ls_table, 3, 0, 0, 0.0f, 25.0f, 0.0f, false);
}

static void build_branching_graph(void) {
    test_graph.node_count = 4;
    test_graph.edge_count = 4;
    test_graph.nodes[0] = {1, 0, 0, 0, true, 25.0f, 80.0f, 0.0f, 1000.0f, 10.0f};
    test_graph.nodes[1] = {2, 0, 10, 0, false, 25.0f, 80.0f, 0.0f, 1000.0f, 8.0f};
    test_graph.nodes[2] = {3, 0, 20, 5, false, 25.0f, 80.0f, 0.0f, 1000.0f, 8.0f};
    test_graph.nodes[3] = {4, 0, 10, 10, true, 25.0f, 80.0f, 0.0f, 1000.0f, 10.0f};
    test_graph.edges[0] = {1, 2, 10.0f, 5, false};
    test_graph.edges[1] = {2, 3, 12.0f, 5, false};
    test_graph.edges[2] = {2, 4, 14.0f, 8, false};
    test_graph.edges[3] = {3, 4, 6.0f, 3, false};

    link_state_init(&ls_table);
    link_state_upsert(&ls_table, 1, 0, 0, 0.0f, 25.0f, 0.0f, false);
    link_state_upsert(&ls_table, 2, 0, 0, 0.0f, 25.0f, 0.0f, false);
    link_state_upsert(&ls_table, 3, 0, 0, 0.0f, 25.0f, 0.0f, false);
    link_state_upsert(&ls_table, 4, 0, 0, 0.0f, 25.0f, 0.0f, false);
}

void test_linear_path(void) {
    build_linear_graph();
    DijkstraResult res = routing_compute(3, &ls_table, &test_graph);
    TEST_ASSERT_FALSE(res.shelter_in_place);
    TEST_ASSERT(res.next_hop == 2);
    TEST_ASSERT(res.cost_to_exit > 0);
    TEST_ASSERT(res.cost_to_exit < SHELTER_THRESHOLD);
}

void test_node_at_exit(void) {
    build_linear_graph();
    DijkstraResult res = routing_compute(1, &ls_table, &test_graph);
    TEST_ASSERT_FALSE(res.shelter_in_place);
    TEST_ASSERT(res.next_hop == 0);
    TEST_ASSERT(res.cost_to_exit == 0);
}

void test_branching_shortest_path(void) {
    build_branching_graph();
    DijkstraResult res = routing_compute(3, &ls_table, &test_graph);
    TEST_ASSERT_FALSE(res.shelter_in_place);
    TEST_ASSERT(res.next_hop == 4);
    TEST_ASSERT(res.cost_to_exit < SHELTER_THRESHOLD);
}

void test_flame_reroutes(void) {
    build_branching_graph();
    link_state_upsert(&ls_table, 4, 1, 0, 0.0f, 200.0f, 800.0f, true);
    link_state_upsert(&ls_table, 3, 1, 0, 0.0f, 25.0f, 0.0f, false);
    DijkstraResult res = routing_compute(2, &ls_table, &test_graph);
    TEST_ASSERT_FALSE_MESSAGE(res.shelter_in_place, "Should reroute around flame");
    TEST_ASSERT(res.next_hop > 0);
    TEST_ASSERT(res.cost_to_exit < SHELTER_THRESHOLD);
}

void test_shelter_when_all_paths_blocked(void) {
    build_branching_graph();
    link_state_upsert(&ls_table, 4, 1, 0, 0.0f, 200.0f, 800.0f, true);
    link_state_upsert(&ls_table, 1, 1, 0, 0.0f, 200.0f, 800.0f, true);
    DijkstraResult res = routing_compute(2, &ls_table, &test_graph);
    TEST_ASSERT_TRUE(res.shelter_in_place);
}

void setup() {
    delay(1000);
    UNITY_BEGIN();
    routing_init();
    RUN_TEST(test_linear_path);
    RUN_TEST(test_node_at_exit);
    RUN_TEST(test_branching_shortest_path);
    RUN_TEST(test_flame_reroutes);
    RUN_TEST(test_shelter_when_all_paths_blocked);
    UNITY_END();
}

void loop() {
    delay(100);
}
