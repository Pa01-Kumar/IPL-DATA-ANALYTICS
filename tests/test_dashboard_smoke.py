"""Execute every Streamlit page against the checked-in project data."""
from streamlit.testing.v1 import AppTest


def test_all_dashboard_pages_render_without_exceptions():
    app = AppTest.from_file("app/dashboard.py", default_timeout=30).run()
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
    page_selector = app.radio[0]
    for page_name in page_names[1:]:
        page_selector.set_value(page_name)
        app.run()
        assert not app.exception, (
            f"Dashboard page {page_name!r} raised an exception: "
            f"{[exception.message for exception in app.exception]}"
        )
