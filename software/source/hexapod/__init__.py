"""Hexapod RPC client helpers used by LiveKit multimodal workers."""

from .rpc_client import HexapodRPCClient, HexapodRPCError, hexapod_call

__all__ = ["HexapodRPCClient", "HexapodRPCError", "hexapod_call"]
