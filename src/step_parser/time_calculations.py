from step_parser.constants import NOTE_TYPES


def calculate_average_bpm(bpm_map, song_length_beats):
    """
    :param bpm_map:
        bpm info for entire song (split list from #BPMS header). eg:
        [(0.0, 150.0), (160.0, 200.0), ..., (<beat>, <bpm>)]
    :param song_length_beats:
        song_measure_count * 4
    :return:
        (
            bpm_weighted_average:   average song BPM weighted by beat count
            bpm_mode:               most common bpm in song
        )
    """
    # keep track of the accumulated number of beats the song
    # spends at each of its bpm values
    bpm_durations = {
        float(bpm): 0
        for _, bpm
        in bpm_map
    }

    last_beat, last_bpm = bpm_map[0]
    for beat, bpm in bpm_map:
        bpm_durations[last_bpm] += 60 * (beat - last_beat) / last_bpm
        last_beat, last_bpm = beat, bpm
    bpm_durations[last_bpm] += 60 * (song_length_beats - last_beat) / last_bpm

    song_duration = sum(bpm_durations.values())
    bpm_weighted_average = sum([
        bpm * duration / song_duration
        for bpm, duration
        in bpm_durations.items()
    ])
    bpm_mode = sorted([
        (bpm, duration)
        for bpm, duration
        in bpm_durations.items()
    ], key=lambda x: x[1])[-1][0]

    return bpm_weighted_average, bpm_mode


def calculate_accumulated_measure_time(bpms, stops):
    """
    :param bpms:
        bpm info for a single measure
        [(0.0, 150.0), (2.0, 200.0), ..., (<beat>, <bpm>)]
    :param stops:
        stop info for a single measure
        [(1.0, "stop", 0.1), (2.0, "stop", 0.2), ..., (<beat>, "stop", <stop len>)]
    :return:
        float - accumulated seconds passed in the measure
    """
    accumulated_seconds = 0
    for _, _, stop in stops:
        accumulated_seconds += stop

    last_beat, last_bpm = bpms[0]
    for beat, bpm in bpms:
        # 60 s/min * beats / (beats/min) => sec
        accumulated_seconds += 60 * (beat - last_beat) / last_bpm
        last_beat, last_bpm = beat, bpm
    # capture the last bpm in the measure. If there were no changes, it's the whole measure
    accumulated_seconds += 60 * (4 - last_beat) / last_bpm

    return accumulated_seconds


def calculate_measure_nps(measure_notes, measure_time_data):
    """
    Assumes 4 beats per measure

    :param measure_notes:       eg. [0001, 1000, 0100, 0010, ...]
    :param measure_time_data:   eg. [(0.0, 165.0), (2.0, 200), (2.0, "stop", 0.1)]
    :return: average notes per second for the measure
    """
    bpms = sorted([i for i in measure_time_data if "stop" not in i], key=lambda x: x[0])
    stops = [i for i in measure_time_data if "stop" in i]

    measure_seconds = calculate_accumulated_measure_time(bpms, stops)

    # Tally up notes, holds, and rolls
    note_count = 0
    for subdivision in measure_notes:
        for note in subdivision:
            if note in NOTE_TYPES:
                note_count += 1

    return float(note_count) / float(measure_seconds)
