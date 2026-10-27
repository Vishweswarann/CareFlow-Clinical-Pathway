import pytest

from src.nightly_bigquery_pipeline import compare_event_ids


def test_first_run_all_events_are_new():
    existing = set()
    incoming = {"EV001", "EV002", "EV003"}

    already_present, new_ids = compare_event_ids(incoming, existing)

    assert already_present == set()
    assert new_ids == incoming


def test_repeat_run_has_no_new_events():
    existing = {"EV001", "EV002", "EV003"}
    incoming = {"EV001", "EV002", "EV003"}

    already_present, new_ids = compare_event_ids(incoming, existing)

    assert already_present == incoming
    assert new_ids == set()


def test_mixed_batch_identifies_only_new_events():
    existing = {"EV001", "EV002"}
    incoming = {"EV002", "EV003", "EV004"}

    already_present, new_ids = compare_event_ids(incoming, existing)

    assert already_present == {"EV002"}
    assert new_ids == {"EV003", "EV004"}


def test_empty_incoming_batch():
    already_present, new_ids = compare_event_ids(set(), {"EV001"})

    assert already_present == set()
    assert new_ids == set()


def test_comparison_does_not_modify_input_sets():
    existing = {"EV001"}
    incoming = {"EV001", "EV002"}

    compare_event_ids(incoming, existing)

    assert existing == {"EV001"}
    assert incoming == {"EV001", "EV002"}