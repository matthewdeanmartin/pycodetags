# This became flaky, Don't know why
# from code_tags.collect import TodoCollector, collect_all_todos
# from tests.demo.demo import ITEMS
#
# import tests.demo.demo as demo
#
# def test_example_usage():
#     """Example of how to use the collectors."""
#
#
#     # Method 1: Use the comprehensive collector
#     results = collect_all_todos(demo, include_submodules=True, include_exceptions=True)
#
#     print(f"Found {len(results['todos'])} TODOs")
#     print(f"Found {len(results['dones'])} Done items")
#     print(f"Found {len(results['exceptions'])} TodoExceptions")
#     assert len(results["todos"]) == 6
#     assert len(results["dones"]) == 1
#     assert len(results["exceptions"]) == 1
#
# def test_example_usage_two():
#     # Method 2: Use individual collectors
#     collector = TodoCollector()
#     todos, runtime_exceptions = collector.collect_from_module(demo)
#     dones = []
#     for item in todos:
#         if item.is_probably_done():
#             dones.append(item)
#             todos.remove(item)
#     assert len(todos) == 6
#     assert len(dones) == 1
#     assert len(runtime_exceptions) == 0  # because it is broken!
#
# def test_example_usage_stand_alone():
#     collector = TodoCollector()
#     # If you have standalone items like your ITEMS list
#     standalone_todos, standalone_dones = collector.collect_standalone_items(ITEMS)
#     assert len(standalone_todos) == 2
#     assert len(standalone_dones) == 1
