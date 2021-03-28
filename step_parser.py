"""
step_parser

Goals:
 * Retrieve metrics for a stepchart
    - measure counter
    - measure breakdown
    - jumps, hands, quads
    - mines
    - notes per second (NPS)
    - peak NPS (for one measure)
    - bpm changes (count, range)
    - crossover count
    - footswitch count
    - jacks count
    - side footswitch count
    ****
    - bracket count
 * parse many stepcharts
    - store data in a csv
    - formatted for feature set consumption

* classify songs as stamina/fa/tech/footspeed?
    - stamina is likely most important -> classify as stamina or not
"""

import argparse
import io
import json
import os
import pandas as pd
import re
import sys
import time

from statistics import mean, median, mode, stdev, StatisticsError

from sm_calculations import calculate_average_bpm
from step_patterns import detect_tech_patterns, detect_jumps_hands_quads


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCE_DIR = os.path.join(ROOT_DIR, "resources")

# These numbers in a stepchart indicate notes that require stepping on
# 1 = note, 2 = hold, 4 = roll
NOTE_TYPES = ["1", "2", "4"]

# .sm keys to extract directly into Stepchart.metadata
METADATA_KEY_TRANSLATIONS = {
    "#TITLE": "title",
    "#ARTIST": "artist",
}


class StepchartException(Exception):
    pass


class NoSinglesChartException(StepchartException):
    pass


class Stepchart(object):
    """
    self.metadata = {
        <difficulty>:
            ...
    }
    """

    def __init__(self, sm_file, stream_note_threshold=14, stream_size_threshold=2):
        self.sm_file = sm_file
        self.stream_note_threshold = stream_note_threshold
        self.stream_size_threshold = stream_size_threshold
        self.difficulties = []
        self.charts = {}
        self.raw_metadata = {}   # put the raw "#TITLE": "blahhhh" key-values in here
        self.time_metadata = {}                 # store bpm and stops
        self.in_measure_time_metadata = []      # store bpm and stop data by measure
        self.metadata = {}       # store desired features here!
        self.streams = []
        self._metadata_generated = False
        self._parse_sm_file()
        self._generate_metadata()

    def _parse_sm_file(self):
        """Reads SM file and populates: difficulties, charts, and metadata"""
        with io.open(self.sm_file, "r") as f:
            sm_contents = f.read()

        # Strip out comments, trailing whitespace
        sm_contents = re.sub(r"//[^\n]*", "", sm_contents)
        sm_contents = re.sub(r"\w$", "", sm_contents)

        raw_content_list = sm_contents.split(";")

        for data_string in raw_content_list:
            header, _, info = data_string.strip("\n").partition(":")
            # some charts have some junk written between a ; and the following #
            header = "".join(header.partition("#")[1:])
            if header.strip() == "#NOTES":
                [
                    step_mode,
                    step_description,
                    step_difficulty,
                    step_rating,
                    step_numbers,
                    step_data
                ] = [i.strip() for i in info.split(":")]
                if step_mode == "dance-single":
                    self.difficulties.append(step_difficulty)
                    self.charts[step_difficulty] = {
                        "mode": step_mode,
                        "description": step_description,
                        "difficulty": step_difficulty,
                        "rating": step_rating,
                        "numbers": step_numbers,
                        "raw_data": step_data
                    }
            else:
                if header.strip():
                    self.raw_metadata[header.strip().upper()] = info

        if len(self.difficulties) == 0:
            raise NoSinglesChartException(f"{self.sm_file} has no dance-single stepcharts")

    def _generate_metadata(self):
        for raw_key, translated_key in METADATA_KEY_TRANSLATIONS.items():
            if raw_key in self.raw_metadata:
                self.metadata[translated_key] = self.raw_metadata[raw_key]

        self._generate_time_metadata()

        for difficulty in self.difficulties:
            if difficulty not in self.metadata:
                self.metadata[difficulty] = {
                    "rating": self.charts[difficulty]["rating"],
                    "difficulty": difficulty,
                }
            if difficulty not in self.raw_metadata:
                self.raw_metadata[difficulty] = {}
            self._generate_measures(difficulty)
            self._generate_stream_breakdown(difficulty)
            self._generate_stream_stats(difficulty)
            self._get_jumps_hands_quads(difficulty)
            self._generate_step_density(difficulty)
            self._generate_tech_metadata(difficulty)

        self._generate_secondary_time_metadata()
        self._metadata_generated = True

    def _generate_measures(self, difficulty=None):
        if difficulty is None:
            difficulty = self.difficulties[0]
        if difficulty not in self.charts:
            raise StepchartException(
                f"{difficulty} not in simfile. Options: {self.difficulties}"
            )

        measure_data = self.charts[difficulty]["raw_data"]
        raw_measures = measure_data.split(',')
        measures = [
            [
                subdivision.strip()
                for subdivision
                in measure.strip().split("\n")
            ]
            for measure
            in raw_measures
            if measure
        ]
        self.charts[difficulty]["measure_list"] = measures
        return measures

    # TODO: make this work with NPS threshold instead note per measure threshold
    def _generate_stream_breakdown(self, difficulty):
        """
        A measure is a "stream" if `self.stream_note_threshold` or more
        subdivisions in that measure have notes

        set self.metadata with count of measures with streams, and return that value
        """
        if not self.charts[difficulty].get("measure_list"):
            self._generate_measures(difficulty)

        measures = self.charts[difficulty]["measure_list"]
        stream_total = 0
        active_measure_counter = 0
        breakdown = []
        in_stream = False

        for measure in measures:
            # counting subdivisions that have notes in them
            subdivision_counter = 0
            if len(measure) >= self.stream_note_threshold:
                for subdivision in measure:
                    if any([i in subdivision for i in NOTE_TYPES]):
                        subdivision_counter += 1

            if subdivision_counter >= self.stream_note_threshold:
                if not in_stream:
                    breakdown.append(f"({active_measure_counter})")
                    active_measure_counter = 0
                in_stream = True
                stream_total += 1
                active_measure_counter += 1
            else:
                if in_stream:
                    breakdown.append(f"{active_measure_counter}")
                    active_measure_counter = 0
                in_stream = False
                active_measure_counter += 1

        # Account for final stream or break
        if in_stream:
            breakdown.append(f"{active_measure_counter}")
        else:
            breakdown.append(f"({active_measure_counter})")

        self.metadata[difficulty]["stream_total"] = stream_total
        self.metadata[difficulty]["breakdown"] = breakdown
        return stream_total, breakdown

    def _generate_stream_stats(self, difficulty):
        if "breakdown" not in self.metadata[difficulty]:
            self._generate_stream_breakdown(difficulty)

        breakdown = self.metadata[difficulty]["breakdown"]
        stream_groups = [
            int(group)
            for group in breakdown
            if not group.startswith("(")
        ]
        break_groups = [
            int(group.strip("(").strip(")"))
            for group in breakdown
            if group.startswith("(")
        ]
        if stream_groups:
            self.metadata[difficulty]["stream_count"] = len(stream_groups)
            self.metadata[difficulty]["stream_size_max"] = max(stream_groups)
            self.metadata[difficulty]["stream_size_avg"] = mean(stream_groups)
            self.metadata[difficulty]["stream_total"] = sum(stream_groups)
            if len(stream_groups) >= 2:
                self.metadata[difficulty]["stream_size_std"] = stdev(stream_groups)

        if len(break_groups) >= 2:
            self.metadata[difficulty]["break_count"] = len(break_groups)
            self.metadata[difficulty]["break_size_max"] = max(break_groups)
            self.metadata[difficulty]["break_size_avg"] = mean(break_groups)
            self.metadata[difficulty]["break_total"] = sum(break_groups)
            if len(break_groups) >= 2:
                self.metadata[difficulty]["break_size_std"] = stdev(break_groups)

        if len(self.charts[difficulty]["measure_list"]) != sum(stream_groups + break_groups):
            print(f"Math bad: {len(self.charts[difficulty]['measure_list'])} != {sum(stream_groups + break_groups)} ")

        self.metadata[difficulty]["measure_count"] = len(self.charts[difficulty]["measure_list"])

        return self.metadata[difficulty]

    def _generate_time_metadata(self):
        if "bpms" not in self.time_metadata:
            raw_bpms = self.raw_metadata["#BPMS"]
            self.time_metadata["bpms"] = sorted([
                [float(x) for x in bpm_change.split("=")]
                for bpm_change in raw_bpms.split(",")
                if bpm_change
            ], key=lambda x: x[0])
        if "stops" not in self.time_metadata:
            raw_stops = self.raw_metadata.get("#STOPS", "")
            self.time_metadata["stops"] = sorted([
                [float(x) for x in stop.split("=")]
                for stop in raw_stops.split(",")
                if stop
            ], key=lambda x: x[0])

        if "bpm_breakdown" not in self.time_metadata:
            sample_difficulty = self.difficulties[0]
            sample_chart_metadata = self.charts[sample_difficulty]
            if "measure_list" not in sample_chart_metadata:
                self._generate_measures(sample_difficulty)
            sample_chart = self.charts[sample_difficulty]["measure_list"]

            # [(measure, beat, bpm), (...]
            bpms = [
                (int(float(beat)) / 4, float(beat) % 4, float(bpm))
                for beat, bpm
                in self.time_metadata["bpms"]
            ]
            stops = [
                (int(float(beat) / 4), float(beat) % 4, float(stop))
                for beat, stop
                in self.time_metadata["stops"]
            ]

            in_measure_time_metadata = []
            previous_measure = None

            for measure_number in range(len(sample_chart)):
                measure_bpms = [
                    (beat, bpm)
                    for measure, beat, bpm in bpms
                    if measure == measure_number
                ]
                measure_stops = [
                    (beat, "stop", stop)
                    for measure, beat, stop in stops
                    if measure == measure_number
                ]

                # If no BPM change, get bpm from last measure
                if not measure_bpms:
                    # if it's the first measure, something is wrong
                    if measure_number == 0:
                        raise StepchartException(f"SM file has no BPM at beat 0: {self.sm_file}")

                    previous_measure_bpms = [i for i in previous_measure if "stop" not in i]
                    _, last_bpm = previous_measure_bpms[-1]
                    measure_bpms = [(0.0, last_bpm)]

                current_measure = sorted(measure_bpms + measure_stops, key=lambda x: x[0])  # noqa
                in_measure_time_metadata.append(current_measure)
                previous_measure = current_measure

            self.in_measure_time_metadata = in_measure_time_metadata

            return self.in_measure_time_metadata

    def _generate_secondary_time_metadata(self):
        # minus one because initial bpm isn't a "change"
        self.metadata["bpm_change_count"] = len(self.time_metadata["bpms"]) - 1
        self.metadata["stop_count"] = len(self.time_metadata["stops"])

        self.metadata["bpm_max"] = max(self.time_metadata["bpms"], key=lambda x: x[1])[1]
        self.metadata["bpm_min"] = min(self.time_metadata["bpms"], key=lambda x: x[1])[1]

        sample_difficulty = self.difficulties[0]
        song_length_beats = self.metadata[sample_difficulty]["measure_count"]
        bpm_weighted_average, bpm_mode = calculate_average_bpm(
            self.time_metadata["bpms"],
            song_length_beats
        )
        self.metadata["bpm_weighted_avg"] = bpm_weighted_average
        self.metadata["bpm_mode"] = bpm_mode

    def _get_measure_bpms(self, measure_number):
        """
        returns a set of BPMs and measure fraction of that BPM change:
        [
            0:    165,      # measure starts at 165 bpm
            0.5:  180       # halfway through the measure (beat 2), bpm changes to 180
        ]
        """
        if not self.in_measure_time_metadata:
            self._generate_time_metadata()
        return self.in_measure_time_metadata[measure_number]

    @staticmethod
    def _calculate_accumulated_measure_time(bpms, stops):
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

    def _calculate_song_length(self):
        if "song_seconds" in self.metadata:
            return self.metadata["song_seconds"]

        if not self.in_measure_time_metadata:
            self._generate_time_metadata()
        time_metadata = self.in_measure_time_metadata
        song_seconds = 0

        for measure_time_data in time_metadata:
            bpms = sorted([i for i in measure_time_data if "stop" not in i], key=lambda x: x[0])
            stops = [i for i in measure_time_data if "stop" in i]
            song_seconds += self._calculate_accumulated_measure_time(bpms, stops)

        self.metadata["song_seconds"] = song_seconds
        return song_seconds

    def _calculate_step_count(self, difficulty):
        if "step_count" in self.metadata[difficulty]:
            return self.metadata[difficulty]["step_count"]

        if not self.charts[difficulty].get("measure_list"):
            self._generate_measures(difficulty)
        measure_list = self.charts[difficulty]["measure_list"]
        step_count = 0
        for measure in measure_list:
            for subdivision in measure:
                for slot in subdivision:
                    if slot in NOTE_TYPES:
                        step_count += 1
        self.metadata[difficulty]["step_count"] = step_count
        return step_count

    def _calculate_measure_nps(self, measure_notes, measure_time_data):
        """
        Assumes 4 beats per measure

        :param measure_notes:       eg. [0001, 1000, 0100, 0010, ...]
        :param measure_time_data:   eg. [(0.0, 165.0), (2.0, 200), (2.0, "stop", 0.1)]
        :return: average notes per second for the measure
        """
        bpms = sorted([i for i in measure_time_data if "stop" not in i], key=lambda x: x[0])
        stops = [i for i in measure_time_data if "stop" in i]

        measure_seconds = self._calculate_accumulated_measure_time(bpms, stops)

        # Tally up notes, holds, and rolls
        note_count = 0
        for subdivision in measure_notes:
            for note in subdivision:
                if note in NOTE_TYPES:
                    note_count += 1

        return float(note_count) / float(measure_seconds)

    def _generate_step_density(self, difficulty):
        if not self.in_measure_time_metadata:
            self._generate_time_metadata()

        if not self.charts[difficulty].get("measure_list"):
            self._generate_measures(difficulty)

        measure_list = self.charts[difficulty]["measure_list"]
        time_metadata = self.in_measure_time_metadata

        step_count = self._calculate_step_count(difficulty)
        song_seconds = self._calculate_song_length()
        song_nps = float(step_count) / float(song_seconds)
        nps_per_measure = []

        for measure_number, measure in enumerate(measure_list):
            if measure_number < len(time_metadata):
                measure_nps = self._calculate_measure_nps(measure, time_metadata[measure_number])
                nps_per_measure.append(measure_nps)

        self.metadata[difficulty]["song_nps"] = song_nps
        self.metadata[difficulty]["nps_per_measure_max"] = max(nps_per_measure)
        self.metadata[difficulty]["nps_per_measure_avg"] = mean(nps_per_measure)
        self.metadata[difficulty]["nps_per_measure_median"] = median(nps_per_measure)
        if len(nps_per_measure) >= 2:
            self.metadata[difficulty]["nps_per_measure_std"] = stdev(nps_per_measure)
        try:
            self.metadata[difficulty]["nps_per_measure_mode"] = mode(nps_per_measure)
        except StatisticsError:
            self.metadata[difficulty]["nps_per_measure_mode"] = "bimodal"

    def _get_jumps_hands_quads(self, difficulty):
        """
        Record the number of jumps, hands, and quads per song.
        Jumps = 2 steps activated at the same time
        Hands = 3 steps activated at the same time, or a jump hold followed by a step
        Quads = 4 steps activated at the same time
        """
        if not self.charts[difficulty].get("measure_list"):
            self._generate_measures(difficulty)

        measures = self.charts[difficulty]["measure_list"]
        jumps, hands, quads, mines, holds, rolls = detect_jumps_hands_quads(measures)

        self.metadata[difficulty]["jumps"] = jumps
        self.metadata[difficulty]["hands"] = hands
        self.metadata[difficulty]["quads"] = quads
        self.metadata[difficulty]["mines"] = mines
        self.metadata[difficulty]["holds"] = holds
        self.metadata[difficulty]["rolls"] = rolls

    def _generate_tech_metadata(self, difficulty):
        (
            crossovers,
            footswitches,
            crossover_footswitches,
            jacks,
            invalid_crossovers
        ) = detect_tech_patterns(self.charts[difficulty]["measure_list"])
        self.metadata[difficulty]["crossovers"] = crossovers
        self.metadata[difficulty]["footswitches"] = footswitches
        self.metadata[difficulty]["crossover_footswitches"] = crossover_footswitches
        self.metadata[difficulty]["jacks"] = jacks
        self.metadata[difficulty]["invalid_crossovers"] = invalid_crossovers

    def metadata_df(self):
        dfs = []
        song_metadata = {
            k: [v]
            for k, v in self.metadata.items()
            if k not in self.difficulties
        }
        for i, difficulty in enumerate(self.difficulties):
            difficulty_metadata = self.metadata[difficulty].copy()
            difficulty_metadata.update(song_metadata)
            difficulty_metadata["breakdown"] = "-".join(difficulty_metadata["breakdown"])
            dfs.append(pd.DataFrame(difficulty_metadata))

        df = pd.concat(dfs, ignore_index=True)
        return df


def analyze_stepchart(sm_file_name):
    stepchart = Stepchart(sm_file_name)
    # print(json.dumps(stepchart.metadata, indent=2))
    df = stepchart.metadata_df()
    return df


def get_sample_files():
    return [
        os.path.join(RESOURCE_DIR, filename)
        for filename in
        os.listdir(RESOURCE_DIR)
    ]


def sample_analysis():
    """
    Do analysis on all .sm files in sample dir and all
    recursive dirs, and return a dataframe of the results.

    if output_file is set, write the results to that file
    as a csv
    """
    sample_df = batch_analysis('resources', "sample_analysis.csv")
    print(sample_df)


def sm_file_search(target_dir):
    sm_files = []
    for root, dirs, files in os.walk(target_dir):
        for name in files:
            file_path = os.path.join(root, name)
            if file_path.endswith(".sm"):
                sm_files.append(file_path)
    return sm_files


def batch_analysis(target_dir, output_file, raise_on_unknown_failure=False):
    sm_files = sm_file_search(target_dir)
    print(
        f"Found {len(sm_files)} .sm files. Running analysis. "
        f"'.'=success, "
        f"'X'=failure, "
        f"'0'=no singles stepchart"
    )
    dfs = []
    sm_file_counter = 0

    for sm_file in sm_files:
        try:
            dfs.append(analyze_stepchart(sm_file))
            print(".", end="", flush=True)
        except UnicodeDecodeError:
            print("X", end="", flush=True)
            with open("errors.log", "a") as f:
                f.writelines([f"ERROR: UnicodeDecodeError - {sm_file}"])
        except NoSinglesChartException:
            print("0", end="", flush=True)
            with open("errors.log", "a") as f:
                f.writelines([f"WARN: - {sm_file} contains no dance-single stepcharts"])
        except Exception as e:
            print("X", end="", flush=True)
            with open("errors.log", "a") as f:
                f.writelines([
                    f"\nERROR: Failed to process {sm_file}\n",
                    str(sys.exc_info()),
                    str(e),
                ])
            if raise_on_unknown_failure:
                print(f"\nERROR: failed to handle {sm_file}")
                raise e
    print("\nAnalysis complete!")
    if len(dfs) >= 1:
        results_df = pd.concat(dfs, ignore_index=True)
    else:
        results_df = pd.DataFrame()
    results_df.to_csv(output_file)
    return results_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target_dir")
    parser.add_argument("output_file", default=f"step_parser_output_{int(time.time())}.csv")
    parser.add_argument("--raise-on-unknown-failure", action="store_true")
    args = parser.parse_args()

    batch_analysis(args.target_dir, args.output_file, args.raise_on_unknown_failure)

    # analyze_stepchart("resources/Fancy Footwork.sm")
    # sample_analysis()

