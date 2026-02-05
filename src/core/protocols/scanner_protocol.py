from typing import Protocol

from src.core.model.model import VillageIdentity, Village, HeroInfo, Account, IncomingAttackInfo


class ScannerProtocol(Protocol):
    """Protocol describing scanning/parsing operations over HTML pages.

    This abstracts the parsing logic currently implemented as free functions
    in `src.scan_adapter.scanner`. Core code (e.g. `Bot`) should depend on
    this protocol so different scanner implementations can be injected.
    """

    def scan_village_list(self, dorf1_html: str) -> list[VillageIdentity]:
        """Parse `/dorf1.php` HTML and return a list of VillageIdentity objects."""

    def scan_village_name(self, dorf1_html: str) -> str:
        """Extract the active village name from `/dorf1.php` HTML."""

    def scan_account_info(self, dorf1_html: str) -> Account:
        """Parse account-level information from `/dorf1.php` HTML and return an Account."""

    def scan_village(self, identity: VillageIdentity, dorf1_html: str, dorf2_html: str) -> Village:
        """Create a full Village model from the two village pages and its identity.

        If provided, movements HTML is parsed to capture incoming attack information.
        """

    def is_reward_available(self, dorf1_html: str) -> bool:
        """Check whether quest/quest-master reward (or similar) is available in the village page."""

    def scan_hero_info(self, hero_attrs_html: str, hero_inventory_html: str) -> HeroInfo:
        """Parse hero attributes and optional inventory HTML and return a HeroInfo object.

        `hero_inventory_html` may be None if inventory page was not fetched.
        """

    def scan_incoming_attacks(self, movements_html: str) -> IncomingAttackInfo:
        """Parse incoming attack count and the next attack timer from movements HTML."""
