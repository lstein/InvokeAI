"""Tests for VRAM usage tracking in invocation stats service."""

from unittest.mock import Mock

import pytest
import torch


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_vram_tracking_with_no_gpu_operations():
    """Test that nodes without GPU operations report 0 VRAM usage."""
    from invokeai.app.services.invocation_stats.invocation_stats_default import InvocationStatsService

    # Create a minimal mock invoker with only what we need
    mock_invoker = Mock()
    mock_invoker.services.model_manager.load.ram_cache.stats = Mock()

    stats_service = InvocationStatsService()
    stats_service.start(mock_invoker)

    # Simulate some initial VRAM being allocated (from previous operations)
    dummy_tensor = torch.zeros((1000, 1000), device="cuda")
    initial_vram = torch.cuda.memory_allocated()
    assert initial_vram > 0, "Should have some VRAM allocated from dummy tensor"

    try:
        # Create a mock invocation that doesn't use GPU
        mock_invocation = Mock()
        mock_invocation.get_type.return_value = "test_node"

        graph_execution_state_id = "test_graph_id"

        # Collect stats for a node that doesn't allocate VRAM
        with stats_service.collect_stats(mock_invocation, graph_execution_state_id):
            # No GPU operations here
            pass

        # Get the stats
        summary = stats_service.get_stats(graph_execution_state_id)
        node_stats = summary.node_stats[0]

        # The peak VRAM should be 0 or very close to 0 since no GPU operations occurred
        assert node_stats.peak_vram_gb < 0.01, (
            f"Expected near-zero VRAM usage for node without GPU operations, but got {node_stats.peak_vram_gb:.3f}G"
        )
    finally:
        # Clean up
        del dummy_tensor
        torch.cuda.empty_cache()


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_vram_tracking_with_reused_cached_memory():
    """Test that nodes reusing cached memory still report VRAM usage.

    This test addresses the issue where nodes like z_image_l2i that reuse
    PyTorch's cached GPU memory were incorrectly showing 0 VRAM usage.
    """
    from invokeai.app.services.invocation_stats.invocation_stats_default import InvocationStatsService

    # Create a minimal mock invoker with only what we need
    mock_invoker = Mock()
    mock_invoker.services.model_manager.load.ram_cache.stats = Mock()

    stats_service = InvocationStatsService()
    stats_service.start(mock_invoker)

    graph_execution_state_id = "test_graph_id_reuse"

    tensor1 = None
    tensor2 = None
    try:
        # First invocation: allocate and then free some VRAM
        mock_invocation_1 = Mock()
        mock_invocation_1.get_type.return_value = "first_gpu_node"

        with stats_service.collect_stats(mock_invocation_1, graph_execution_state_id):
            tensor1 = torch.zeros((5000, 5000), device="cuda")  # ~100MB

        # Free the tensor but keep it in PyTorch's cache
        del tensor1
        tensor1 = None

        # Second invocation: allocate memory that fits in the cache
        # This should still show VRAM usage even though it's reusing cached memory
        mock_invocation_2 = Mock()
        mock_invocation_2.get_type.return_value = "second_gpu_node_reuses_cache"

        with stats_service.collect_stats(mock_invocation_2, graph_execution_state_id):
            tensor2 = torch.zeros((4000, 4000), device="cuda")  # ~64MB, fits in cached space

        # Get the stats
        summary = stats_service.get_stats(graph_execution_state_id)

        # Find stats for each node type
        node_stats_dict = {stat.node_type: stat for stat in summary.node_stats}

        # Both nodes should show VRAM usage
        assert node_stats_dict["first_gpu_node"].peak_vram_gb > 0.05, (
            f"First GPU node should show VRAM usage, got {node_stats_dict['first_gpu_node'].peak_vram_gb:.3f}G"
        )

        # This is the critical test - the second node should NOT show 0 even though
        # it's reusing cached memory
        assert node_stats_dict["second_gpu_node_reuses_cache"].peak_vram_gb > 0.03, (
            f"Second GPU node should show VRAM usage even when reusing cache, "
            f"got {node_stats_dict['second_gpu_node_reuses_cache'].peak_vram_gb:.3f}G"
        )
    finally:
        # Clean up
        if tensor1 is not None:
            del tensor1
        if tensor2 is not None:
            del tensor2
        torch.cuda.empty_cache()


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_vram_tracking_with_gpu_operations():
    """Test that nodes with GPU operations report correct VRAM usage."""
    from invokeai.app.services.invocation_stats.invocation_stats_default import InvocationStatsService

    # Create a minimal mock invoker with only what we need
    mock_invoker = Mock()
    mock_invoker.services.model_manager.load.ram_cache.stats = Mock()

    stats_service = InvocationStatsService()
    stats_service.start(mock_invoker)

    # Create a mock invocation
    mock_invocation = Mock()
    mock_invocation.get_type.return_value = "test_gpu_node"

    graph_execution_state_id = "test_graph_id_2"

    test_tensor = None
    try:
        # Collect stats for a node that allocates VRAM
        with stats_service.collect_stats(mock_invocation, graph_execution_state_id):
            # Allocate a significant amount of VRAM
            test_tensor = torch.zeros((10000, 10000), device="cuda")  # ~400MB

        # Get the stats
        summary = stats_service.get_stats(graph_execution_state_id)
        node_stats = summary.node_stats[0]

        # The peak VRAM should reflect the allocation we made (roughly 400MB = 0.4GB)
        assert node_stats.peak_vram_gb > 0.1, (
            f"Expected significant VRAM usage for node with GPU operations, but got {node_stats.peak_vram_gb:.3f}G"
        )
    finally:
        # Clean up
        if test_tensor is not None:
            del test_tensor
        torch.cuda.empty_cache()


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_vram_tracking_multiple_invocations():
    """Test that VRAM tracking works correctly across multiple invocations."""
    from invokeai.app.services.invocation_stats.invocation_stats_default import InvocationStatsService

    # Create a minimal mock invoker with only what we need
    mock_invoker = Mock()
    mock_invoker.services.model_manager.load.ram_cache.stats = Mock()

    stats_service = InvocationStatsService()
    stats_service.start(mock_invoker)

    graph_execution_state_id = "test_graph_id_3"

    tensor1 = None
    tensor2 = None
    try:
        # First invocation: allocate some VRAM
        mock_invocation_1 = Mock()
        mock_invocation_1.get_type.return_value = "gpu_node"

        with stats_service.collect_stats(mock_invocation_1, graph_execution_state_id):
            tensor1 = torch.zeros((5000, 5000), device="cuda")  # ~100MB

        # Second invocation: no GPU operations (this is the key test)
        mock_invocation_2 = Mock()
        mock_invocation_2.get_type.return_value = "cpu_node"

        with stats_service.collect_stats(mock_invocation_2, graph_execution_state_id):
            # No GPU operations, but VRAM is still allocated from previous invocation
            pass

        # Third invocation: more GPU operations
        mock_invocation_3 = Mock()
        mock_invocation_3.get_type.return_value = "another_gpu_node"

        with stats_service.collect_stats(mock_invocation_3, graph_execution_state_id):
            tensor2 = torch.zeros((5000, 5000), device="cuda")  # ~100MB

        # Get the stats
        summary = stats_service.get_stats(graph_execution_state_id)

        # Find stats for each node type
        node_stats_dict = {stat.node_type: stat for stat in summary.node_stats}

        # First node should show VRAM usage
        assert node_stats_dict["gpu_node"].peak_vram_gb > 0.05, (
            f"First GPU node should show VRAM usage, got {node_stats_dict['gpu_node'].peak_vram_gb:.3f}G"
        )

        # Second node (CPU-only) should show minimal or zero VRAM usage
        # This is the critical test - it should NOT show the VRAM from the previous node
        assert node_stats_dict["cpu_node"].peak_vram_gb < 0.01, (
            f"CPU node should show near-zero VRAM usage even with prior allocations, "
            f"got {node_stats_dict['cpu_node'].peak_vram_gb:.3f}G"
        )

        # Third node should show VRAM usage
        assert node_stats_dict["another_gpu_node"].peak_vram_gb > 0.05, (
            f"Third GPU node should show VRAM usage, got {node_stats_dict['another_gpu_node'].peak_vram_gb:.3f}G"
        )
    finally:
        # Clean up
        if tensor1 is not None:
            del tensor1
        if tensor2 is not None:
            del tensor2
        torch.cuda.empty_cache()
