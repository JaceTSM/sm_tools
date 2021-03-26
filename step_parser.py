"""
step_parser

Goals:
 * Retrieve metrics for a stepchart
    - measure counter
    - measure breakdown
    ****
    - jumps, hands, quads
    - mines
    - notes per second (NPS)
    - peak NPS (for one measure)
    - crossover count
    - footswitch count
    - jacks count
    - side footswitch count
    - bracket count
    - bpm changes (count, range)
 * parse many stepcharts
    - store data in a csv
    - formatted for feature set consumption

* classify songs as stamina/fa/tech/footspeed?
    - stamina is likely most important -> classify as stamina or not
"""

import json
import numpy
import os
import re
import sys

import pandas as pd


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
        self.time_metadata = {}  # store bpm and stop info here
        self.metadata = {}       # store desired features here!
        self.streams = []
        self._parse_sm_file()
        self._generate_metadata()

    def _parse_sm_file(self):
        """Reads SM file and populates: difficulties, charts, and metadata"""
        with open(self.sm_file, "r") as f:
            sm_contents = f.read()

        # Strip out comments, trailing whitespace
        sm_contents = re.sub("//[^\n]*", "", sm_contents)
        sm_contents = re.sub("\w$", "", sm_contents)

        raw_content_list = sm_contents.split(";")

        for data_string in raw_content_list:
            header, _, info = data_string.strip("\n").partition(":")
            if header.strip() == "#NOTES":
                [
                    step_mode,
                    step_description,
                    step_difficulty,
                    step_rating,
                    step_numbers,
                    step_data
                ] = [i.strip() for i in info.split(":")]
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
                    self.raw_metadata[header.strip()] = info

    def _generate_metadata(self):
        for raw_key, translated_key in METADATA_KEY_TRANSLATIONS.items():
            if raw_key in self.raw_metadata:
                self.metadata[translated_key] = self.raw_metadata[raw_key]

        self._generate_time_metadata()

        for difficulty in self.difficulties:
            if difficulty not in self.metadata:
                self.metadata[difficulty] = {}
            if difficulty not in self.raw_metadata:
                self.raw_metadata[difficulty] = {}
            self._generate_measures(difficulty)
            self._generate_stream_breakdown(difficulty)
            self._generate_stream_stats(difficulty)
            self._get_jumps_hands_quads(difficulty)

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
            measure.strip().split("\n")
            for measure
            in raw_measures
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
        self.metadata[difficulty]["stream_count"] = len(stream_groups)
        self.metadata[difficulty]["stream_size_max"] = max(stream_groups)
        self.metadata[difficulty]["stream_size_avg"] = sum(stream_groups) / len(stream_groups)
        self.metadata[difficulty]["stream_size_std"] = numpy.std(stream_groups)
        self.metadata[difficulty]["stream_total"] = sum(stream_groups)

        self.metadata[difficulty]["break_count"] = len(break_groups)
        self.metadata[difficulty]["break_size_max"] = max(break_groups)
        self.metadata[difficulty]["break_size_avg"] = sum(break_groups) / len(break_groups)
        self.metadata[difficulty]["break_size_std"] = numpy.std(break_groups)
        self.metadata[difficulty]["break_total"] = sum(break_groups)

        if len(self.charts[difficulty]["measure_list"]) != sum(stream_groups + break_groups):
            print(f"Math bad: {len(self.charts[difficulty]['measure_list'])} != {sum(stream_groups + break_groups)} ")

        self.metadata[difficulty]["measure_count"] = len(self.charts[difficulty]["measure_list"])

        return self.metadata[difficulty]

    def _generate_time_metadata(self):
        if "bpms" not in self.time_metadata:
            raw_bpms = self.raw_metadata["#BPMS"]
            self.time_metadata["bpms"] = sorted([
                bpm_change.split("=")
                for bpm_change in raw_bpms.split(",")
            ], key=lambda x: x[0])
        if "stops" not in self.time_metadata:
            raw_stops = self.raw_metadata["#STOPS"]
            self.time_metadata["stops"] = sorted([
                bpm_change.split("=")
                for bpm_change in raw_stops.split(",")
            ], key=lambda x: x[0])
        if "bpm_breakdown" not in self.time_metadata:
            time_metadata = []
            sample_chart = self.charts[self.difficulties[0]]["measure_list"]
            measure_count = len(sample_chart)
            current_bpm = self.time_metadata["bpms"][0][1]  # Starting bpm
            for measure_number in range(measure_count):
                pass
                # TODO: create list of measures with bpms and stops per measure,
                #  like in comments in the method below this one

    def _get_measure_bpms(self, measure_number):
        """
        returns a set of BPMs and measure fraction of that BPM change:
        [
            0:    165,      # measure starts at 165 bpm
            0.5:  180       # halfway through the measure (beat 2), bpm changes to 180
        ]
        """
        self._generate_time_metadata()

        bpms = self.metadata["bpms"]
        stops = self.metadata["stops"]





    def _calculate_step_density(self, difficulty):
        if not self.charts[difficulty].get("measure_list"):
            self._generate_measures(difficulty)

        measures = self.charts[difficulty]["measure_list"]

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
        jumps = hands = quads = 0
        for measure in measures:
            for subdivision in measure:
                arrow_counter = 0
                #indexing each possible step per row
                for i in range(0, 4):
                    if subdivision[i] in NOTE_TYPES:
                        arrow_counter += 1
                if arrow_counter == 2:
                    jumps += 1
                elif arrow_counter == 3:
                    hands += 1
                elif arrow_counter == 4:
                    quads += 1
        self.metadata[difficulty]["jumps"] = jumps
        self.metadata[difficulty]["hands"] = hands
        self.metadata[difficulty]["quads"] = quads
        return jumps, hands, quads


def analyze_stepchart(sm_file_name, difficulty="Challenge"):
    stepchart = Stepchart(sm_file_name)

    # step_count = stepchart.metadata[difficulty]["step_count"]
    # breakdown = stepchart.metadata[difficulty]["breakdown"]
    # print(step_count)
    # print(breakdown)
    print(json.dumps(stepchart.metadata, indent=2))

    # return stepchart.get_analysis(difficulty)


def get_sample_files():
    return [
        os.path.join(RESOURCE_DIR, filename)
        for filename in
        os.listdir(RESOURCE_DIR)
    ]


def batch_analysis(target_dir, output_file=None):
    """
    Do analysis on all .sm files in target dir and all
    recursive dirs, and return a dataframe of the results.

    if output_file is set, write the results to that file
    as a csv
    """
    analyses = {}
    for sample_file in get_sample_files():
        analyses[sample_file] = analyze_stepchart(sample_file)

    # Make DF out of analyses
    # write DF to csv


if __name__ == "__main__":
    analyze_stepchart("resources/Blade.sm", "Challenge")
    # print(get_sample_files())
