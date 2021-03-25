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
import os
import re
import sys

import pandas as pd


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCE_DIR = os.path.join(ROOT_DIR, "resources")


class StepchartException(Exception):
    pass


class Stepchart(object):
    def __init__(self, sm_file):
        self.sm_file = sm_file
        self.difficulties = []
        self.charts = {}
        self.metadata = {}
        self.streams = []
        self._parse_sm_file()

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
                step_mode, step_description, step_difficulty, step_rating, step_numbers, step_data = info.split(":")
                self.difficulties.append(step_difficulty)
                self.charts[step_difficulty.strip()] = {
                    "mode": step_mode.strip(),
                    "description": step_description.strip(),
                    "difficulty": step_difficulty.strip(),
                    "rating": step_rating.strip(),
                    "numbers": step_numbers.strip(),
                    "raw_data": step_data.strip()
                }
            else:
                if header.strip():
                    self.metadata[header.strip()] = info

    def generate_measures(self, difficulty=None):
        if difficulty is None:
            difficulty = self.difficulties[0]
        if difficulty not in self.charts:
            raise StepchartException(
                f"{difficulty} not it simfile. Options: {self.difficulties}"
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
    def get_stream_breakdown(self, difficulty, threshold=14):
        """
        Stream:
        * 14 or more subdivisions in a measure with notes

        return N - count of measures with streams
        """
        if not self.charts[difficulty].get("measure_list"):
            self.generate_measures(difficulty)

        measures = self.charts[difficulty]["measure_list"]
        stream_count = 0
        active_measure_counter = 0
        breakdown = []
        in_stream = False

        for measure in measures:
            # counting subdivisions that have notes in them
            subdivision_counter = 0
            if len(measure) >= threshold:
                for subdivision in measure:
                    # 1 = note, 2 = hold, 3 = roll
                    if "1" in subdivision or \
                            "2" in subdivision or \
                            "4" in subdivision:
                        subdivision_counter += 1

            if subdivision_counter >= threshold:
                if not in_stream:
                    breakdown.append(f"({active_measure_counter})")
                    active_measure_counter = 0
                in_stream = True
                stream_count += 1
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

        self.metadata["stream_count"] = stream_count
        self.metadata["breakdown"] = breakdown
        return stream_count, breakdown




def analyze_stepchart(sm_file_name, difficulty="Challenge"):
    stepchart = Stepchart(sm_file_name)

    step_count, breakdown = stepchart.get_stream_breakdown("Medium")
    print(step_count)
    print(breakdown)
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
    analyze_stepchart("resources/Endless Flyer.sm", "Challenge")
    # print(get_sample_files())
