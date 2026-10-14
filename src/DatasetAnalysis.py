import pandas
import pm4py


def DatasetDetails():
    df = pandas.read_csv("../data/sample/ehr_events_sample.csv")

    event_log = pm4py.format_dataframe(
        df,
        case_id="case_id",
        activity_key="activity",
        timestamp_key="timestamp",
        timest_format="%y-%m-%d %H:%M:%S",
    )
    # 2026-01-02 22:59:48
    #
    # print(event_log)
    #
    # start_activity = pm4py.get_start_activities(event_log)
    # end_activity = pm4py.get_end_activities(event_log)
    #
    # print(start_activity)
    # print(end_activity)

    print(pm4py.filter_start_activities(event_log, "Registration", True))


if __name__ == "__main__":
    DatasetDetails()
