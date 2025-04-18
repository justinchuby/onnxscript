# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
from __future__ import annotations

import logging

import onnxscript.ir.passes.common.constant_manipulation
import onnxscript.ir.passes.common.unused_removal
from onnxscript import ir, rewriter
from onnxscript.optimizer import _constant_folding, _inliner

logger = logging.getLogger(__name__)


def optimize_ir(
    model: ir.Model,
    num_iterations: int = 2,
    *,
    onnx_shape_inference: bool = True,
    stop_if_no_change: bool = True,
    input_size_limit: int = _constant_folding.DEFAULT_CONSTANT_FOLD_INPUT_SIZE_LIMIT,
    output_size_limit: int = _constant_folding.DEFAULT_CONSTANT_FOLD_OUTPUT_SIZE_LIMIT,
) -> None:
    """Optimizes a model.

    Args:
        model: The model to be optimized.
        num_iterations: Number of times the optimization loop is repeated.
        onnx_shape_inference: Applies node-level shape-inference as part of optimization
        input_size_limit: Will not apply constant folding to ops with any input of size
            greater than this. Does not apply to special ops like Shape() and Size().
        output_size_limit: Will not rewrite any foldable-op into a Constant op if the size
            of the output tensor is greater than this.
        stop_if_no_change: Not supported currently (has no effect). Meant to stop the
            outer optimization loop if no change is detected in one iteration.
    """
    optimizer_pass = ir.passes.Sequential(
        _inliner.InlinePass(),
        ir.passes.PassManager(
            [
                _constant_folding.FoldConstantsPass(
                    external_data_folder="",
                    shape_inference=onnx_shape_inference,
                    input_size_limit=input_size_limit,
                    output_size_limit=output_size_limit,
                ),
                rewriter.RewritePass(rewriter._DEFAULT_REWRITE_RULES),
                onnxscript.ir.passes.common.unused_removal.RemoveUnusedNodesPass(),
                onnxscript.ir.passes.common.unused_removal.RemoveUnusedFunctionsPass(),
                onnxscript.ir.passes.common.unused_removal.RemoveUnusedOpsetsPass(),
            ],
            steps=num_iterations,
            early_stop=stop_if_no_change,
        ),
        onnxscript.ir.passes.common.unused_removal.RemoveUnusedNodesPass(),
        onnxscript.ir.passes.common.constant_manipulation.LiftConstantsToInitializersPass(),
    )
    assert optimizer_pass.in_place
    result = optimizer_pass(model)
    assert result.model is model
