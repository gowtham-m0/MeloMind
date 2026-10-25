"""link_journal step 4, `save` (code): the suggestions, through `propose_links`. They stay
suggestions until the user confirms each one (rule 4)."""

from app.application.agent.resolve_state import LinkDeps, LinkState
from app.application.agent.tools.journal_links import LinkProposal, propose_links

NODE = "save"


async def save_suggestions(state: LinkState, deps: LinkDeps) -> LinkState:
    """Store the suggested links."""
    proposals = [
        LinkProposal(target=target.node, is_new=target.is_new, reason=target.reason)
        for target in state.get("targets", [])
    ]
    saved = await propose_links(
        deps.journal, deps.log, deps.profile_id, NODE, state["entry"].id, proposals
    )
    return {"suggested": saved}
