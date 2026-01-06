"""Asterisk dialplan configuration generator - Main coordinator."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .inbound_router import InboundRouter
from .extension_router import ExtensionRouter
from .outbound_policy import OutboundPolicyGenerator

logger = logging.getLogger(__name__)


class DialplanGenerator:
    """
    Main dialplan generator coordinator.

    Combines outputs from specialized generators:
    - InboundRouter: DID routing from trunks
    - ExtensionRouter: Internal extension-to-extension dialing
    - OutboundPolicyGenerator: Outbound calling policy enforcement

    This refactored design separates concerns for easier maintenance.
    """

    @staticmethod
    def generate_config(
        users_with_extensions: Optional[List[Dict[str, Any]]] = None,
        dids: Optional[List[Dict[str, Any]]] = None,
        policies: Optional[List[Dict[str, Any]]] = None,
        tenants: Optional[List[Dict[str, Any]]] = None,
        did_assignments: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Generate complete dialplan configuration.

        Args:
            users_with_extensions: List of user dicts (for compatibility)
            dids: List of DID configuration dicts (optional, legacy)
            policies: List of outbound policy dicts (optional)
            tenants: List of tenant dicts (optional)
            did_assignments: List of DID assignment dicts (new, preferred over dids)

        Returns:
            str: Complete Asterisk dialplan configuration

        Example:
            >>> config = DialplanGenerator.generate_config(
            ...     users_with_extensions=users,
            ...     did_assignments=did_assignments,
            ...     policies=policies,
            ...     tenants=tenants
            ... )
        """
        logger.info("Generating complete dialplan configuration")

        config_parts = []

        # Header
        config_parts.append(DialplanGenerator._generate_header())
        config_parts.append("")

        # Inbound routing (if DID assignments or legacy DIDs provided)
        if did_assignments is not None:
            logger.info(f"Generating inbound routing for {len(did_assignments)} DID assignments")
            inbound_config = InboundRouter.generate(
                did_assignments=did_assignments,
                users=users_with_extensions or []
            )
            config_parts.append(inbound_config)
            config_parts.append("")
        elif dids and users_with_extensions:
            logger.info(f"Generating inbound routing for {len(dids)} DIDs (legacy)")
            inbound_config = InboundRouter.generate(dids=dids, users=users_with_extensions)
            config_parts.append(inbound_config)
            config_parts.append("")

        # Internal extension routing
        if users_with_extensions and tenants:
            logger.info(f"Generating internal routing for {len(users_with_extensions)} users")
            extension_config = ExtensionRouter.generate(users_with_extensions, tenants)
            config_parts.append(extension_config)
            config_parts.append("")
        elif users_with_extensions:
            # Fallback to simple routing if tenants not provided (backward compatibility)
            logger.info("Generating simple internal routing (no tenant separation)")
            config_parts.append(DialplanGenerator._generate_simple_internal(users_with_extensions))
            config_parts.append("")

        # Outbound policy enforcement (if policies provided)
        if policies:
            logger.info(f"Generating outbound policies for {len(policies)} policies")
            outbound_config = OutboundPolicyGenerator.generate(policies, users_with_extensions or [])
            config_parts.append(outbound_config)
            config_parts.append("")

        config = "\n".join(config_parts)
        logger.info(f"Complete dialplan generated: {len(config.splitlines())} lines")
        return config

    @staticmethod
    def _generate_header() -> str:
        """Generate configuration file header."""
        return f"""; ========================================
; PBX Control Portal - Dialplan Configuration
; ========================================
; Generated: {datetime.utcnow().isoformat()}Z
; DO NOT EDIT MANUALLY - Changes will be overwritten on next apply
;
; This file is generated from database configuration and includes:
; - Inbound DID routing ([from-trunk])
; - Internal extension dialing ([internal-*])
; - Outbound calling policies ([outbound])
;"""

    @staticmethod
    def _generate_simple_internal(users: List[Dict[str, Any]]) -> str:
        """
        Generate simple internal routing (backward compatibility).

        Args:
            users: List of user dicts

        Returns:
            str: Simple internal routing configuration
        """
        lines = []
        lines.append("[synergy-internal]")
        lines.append("; Simple internal extension routing")
        lines.append("")

        for user in users:
            ext_data = user.get("extension")
            if isinstance(ext_data, dict):
                ext = ext_data.get("number")
            elif isinstance(ext_data, int):
                ext = ext_data
            else:
                continue

            if ext:
                lines.append(f"exten => {ext},1,Dial(PJSIP/{ext},20)")
                lines.append(f"exten => {ext},n,Hangup()")
                lines.append("")

        return "\n".join(lines)
