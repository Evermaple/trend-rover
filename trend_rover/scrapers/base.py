from abc import ABC, abstractmethod
from datetime import date

from trend_rover.models import Feed


class BaseScraper(ABC):
    @abstractmethod
    def search(
        self,
        keyword: str,
        start_date: date,
        end_date: date,
        **filters,
    ) -> list[Feed]:
        """Search for feeds matching keyword in date range."""

    @abstractmethod
    def get_stats(self, feed_id: str) -> Feed:
        """Fetch latest engagement stats for a single feed."""
