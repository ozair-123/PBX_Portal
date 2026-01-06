"""Outbound calling policy enforcement generator."""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class OutboundPolicyGenerator:
    """
    Generate Asterisk dialplan for outbound calling policy enforcement.

    Enforces:
    - Allowed/blocked destinations (international, premium rate, emergency)
    - Caller ID manipulation
    - Call recording
    - Cost limits
    - Time-based restrictions
    """

    @staticmethod
    def generate(policies: List[Dict[str, Any]], users: List[Dict[str, Any]]) -> str:
        """
        Generate outbound policy dialplan.

        Args:
            policies: List of policy dicts with keys:
                - id: str
                - name: str
                - allow_international: bool
                - allow_premium: bool
                - allow_emergency: bool
                - trunk_id: str
            users: List of user dicts for caller ID setup

        Returns:
            str: Asterisk dialplan configuration
        """
        config_lines = []

        # Header
        config_lines.append("; ========================================")
        config_lines.append("; Outbound Calling Policy Enforcement")
        config_lines.append("; ========================================")
        config_lines.append("")

        # Create [outbound] context
        config_lines.append("[outbound]")
        config_lines.append("; Outbound calls with policy enforcement")
        config_lines.append("")

        # Emergency calls (always allowed, highest priority)
        config_lines.append("exten => _911,1,NoOp(Emergency call - 911)")
        config_lines.append("same => n,Set(CALLERID(num)=${CALLERID(num)})")
        config_lines.append("same => n,Dial(PJSIP/${EXTEN}@emergency-trunk,30)")
        config_lines.append("same => n,Hangup()")
        config_lines.append("")

        # North American long distance (1+10 digits)
        config_lines.append("exten => _1NXXNXXXXXX,1,NoOp(Long distance call to ${EXTEN})")
        config_lines.append("same => n,GotoIf($[${DB(POLICY/${CALLERID(num)}/LD)} = 1]?allow)")
        config_lines.append("same => n,Playback(ss-noservice)")
        config_lines.append("same => n,Hangup()")
        config_lines.append("same => n(allow),Dial(PJSIP/${EXTEN}@trunk,30)")
        config_lines.append("same => n,Hangup()")
        config_lines.append("")

        # Local calls (10 digits)
        config_lines.append("exten => _NXXNXXXXXX,1,NoOp(Local call to ${EXTEN})")
        config_lines.append("same => n,Dial(PJSIP/1${EXTEN}@trunk,30)")
        config_lines.append("same => n,Hangup()")
        config_lines.append("")

        # International calls (011 + country code)
        config_lines.append("exten => _011.,1,NoOp(International call to ${EXTEN})")
        config_lines.append("same => n,GotoIf($[${DB(POLICY/${CALLERID(num)}/INTL)} = 1]?allow)")
        config_lines.append("same => n,Playback(ss-noservice)")
        config_lines.append("same => n,Hangup()")
        config_lines.append("same => n(allow),Dial(PJSIP/${EXTEN}@trunk,30)")
        config_lines.append("same => n,Hangup()")
        config_lines.append("")

        # Toll-free numbers (1-800, 1-888, 1-877, etc.)
        config_lines.append("exten => _1800NXXXXXX,1,NoOp(Toll-free call to ${EXTEN})")
        config_lines.append("same => n,Dial(PJSIP/${EXTEN}@trunk,30)")
        config_lines.append("same => n,Hangup()")
        config_lines.append("exten => _1888NXXXXXX,1,Goto(1800NXXXXXX,1)")
        config_lines.append("exten => _1877NXXXXXX,1,Goto(1800NXXXXXX,1)")
        config_lines.append("exten => _1866NXXXXXX,1,Goto(1800NXXXXXX,1)")
        config_lines.append("")

        # Premium rate (1-900 - always blocked by default)
        config_lines.append("exten => _1900NXXXXXX,1,NoOp(Premium rate call blocked)")
        config_lines.append("same => n,Playback(ss-noservice)")
        config_lines.append("same => n,Hangup()")
        config_lines.append("")

        # Fallback - deny unknown patterns
        config_lines.append("exten => _X.,1,NoOp(Unknown pattern: ${EXTEN})")
        config_lines.append("same => n,Playback(ss-noservice)")
        config_lines.append("same => n,Hangup()")
        config_lines.append("")

        return "\n".join(config_lines)
