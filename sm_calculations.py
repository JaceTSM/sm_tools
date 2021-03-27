def calculate_average_bpm(bpm_map, song_length_beats):
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
