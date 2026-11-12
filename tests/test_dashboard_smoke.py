"""Execute every Streamlit page against the checked-in project data."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_all_dashboard_pages_render_without_exceptions():
    app = AppTest.from_file(ROOT / "app" / "dashboard.py", default_timeout=30).run()
    assert not app.exception, [exception.message for exception in app.exception]

    page_names = [
        "Overview",
        "Player Profile",
        "Team Comparison",
        "Venue Insights",
        "Matchup Explorer",
        "Player Impact",
        "Win Probability",
        "Player Shortlist",
    ]
    for page_name in page_names[1:]:
        app.radio[0].set_value(page_name)
        app.run()
        assert not app.exception, (
            f"Dashboard page {page_name!r} raised an exception: "
            f"{[exception.message for exception in app.exception]}"
        )
