"""Internal extension-to-extension routing generator."""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ExtensionRouter:
    """
    Generate Asterisk dialplan for internal extension-to-extension dialing.

    Handles:
    - Direct extension dialing within a tenant
    - Call forwarding
    - Do Not Disturb (DND)
    - Voicemail on no answer/busy
    """

    @staticmethod
    def generate(users: List[Dict[str, Any]], tenants: List[Dict[str, Any]]) -> str:
        """
        Generate internal extension routing dialplan.

        Args:
            users: List of user dicts with keys:
                - id: str
                - tenant_id: str
                - extension: int
                - name: str
                - dnd_enabled: bool
                - call_forward_destination: str (optional)
                - voicemail_enabled: bool
            tenants: List of tenant dicts with keys:
                - id: str
                - name: str
                - ext_min: int
                - ext_max: int

        Returns:
            str: Asterisk dialplan configuration
        """
        config_lines = []

        # Header
        config_lines.append("; ========================================")
        config_lines.append("; Internal Extension Routing")
        config_lines.append("; ========================================")
        config_lines.append("")

        # Group users by tenant
        users_by_tenant: Dict[str, List[Dict[str, Any]]] = {}
        for user in users:
            tenant_id = user.get("tenant_id")
            if tenant_id:
                if tenant_id not in users_by_tenant:
                    users_by_tenant[tenant_id] = []
                users_by_tenant[tenant_id].append(user)

        # Create [internal] context for each tenant
        for tenant in tenants:
            tenant_id = tenant.get("id")
            tenant_name = tenant.get("name", "Unknown")
            tenant_users = users_by_tenant.get(tenant_id, [])

            config_lines.append(f"; Tenant: {tenant_name}")
            config_lines.append(f"[internal-{tenant_id}]")
            config_lines.append("")

            # Create routing for each user extension
            for user in tenant_users:
                ext = user.get("extension")
                if not ext:
                    continue

                name = user.get("name", "User")
                dnd_enabled = user.get("dnd_enabled", False)
                forward_dest = user.get("call_forward_destination")
                vm_enabled = user.get("voicemail_enabled", True)

                config_lines.append(f"exten => {ext},1,NoOp(Call to {name} - Ext {ext})")

                # Check DND
                if dnd_enabled:
                    config_lines.append(f"same => n,GotoIf(${{DB(DND/{ext})}}?dnd)")

                # Check call forwarding
                if forward_dest:
                    config_lines.append(f"same => n,GotoIf(${{DB(CFW/{ext})}}?forward)")

                # Normal dial
                config_lines.append(f"same => n(dial),Set(CALLERID(name)={name})")
                config_lines.append(f"same => n,Dial(PJSIP/{ext},30,tr)")

                # No answer - go to voicemail if enabled
                if vm_enabled:
                    config_lines.append(f"same => n,Voicemail({ext}@default,u)")
                else:
                    config_lines.append(f"same => n,Playback(im-sorry)")

                config_lines.append(f"same => n,Hangup()")

                # DND label
                if dnd_enabled:
                    config_lines.append(f"same => n(dnd),Playback(do-not-disturb)")
                    if vm_enabled:
                        config_lines.append(f"same => n,Voicemail({ext}@default,u)")
                    config_lines.append(f"same => n,Hangup()")

                # Call forward label
                if forward_dest:
                    config_lines.append(f"same => n(forward),Dial(PJSIP/{forward_dest},30)")
                    if vm_enabled:
                        config_lines.append(f"same => n,Voicemail({ext}@default,u)")
                    config_lines.append(f"same => n,Hangup()")

                config_lines.append("")

            # Fallback for invalid extensions
            config_lines.append("exten => _X.,1,NoOp(Invalid extension: ${EXTEN})")
            config_lines.append("same => n,Playback(ss-noservice)")
            config_lines.append("same => n,Hangup()")
            config_lines.append("")

        return "\n".join(config_lines)
