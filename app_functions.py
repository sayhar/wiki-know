#!/usr/bin/env python3
# app_functions

# This defines the following functions called by hello.py:

# result_guess(testname, batch, guess)
# show_noguess(testname, batch)
# ask_guess(testname, batch)
# show_dir(batch, MODE)
# It relies on functions in app_helper.py

from flask import render_template
from os.path import join
import csv
import logging

logger = logging.getLogger(__name__)


class AppFunctions:
    def __init__(self, theapp, helper):
        self.app = theapp
        self.h = helper

    def result_guess(self, testname, batch, guess):
        # Show the result of the guess. Only in guess mode.
        # Used to be called show_winner
        winner_row, dirname = self.h.win_dir(testname)

        if winner_row is None:
            return (
                render_template(
                    "error.html",
                    batch=batch,
                    why="Incorrect Test Name",
                    secret=winner_row,
                ),
                404,
            )

        if not self.h.test_in_batch(testname, batch):
            return (
                render_template(
                    "error.html",
                    batch=batch,
                    why="Ordering scheme: " + batch + " not found",
                    title="Err...",
                ),
                404,
            )

        stats = self.h.row_stats(winner_row)
        guessstats = self.h.guess_stats(winner_row, dirname, guess)
        tables = self.h.get_tables(dirname)
        diagnostic_charts = self.h.get_diagnostic_charts(dirname)
        info = self.h.get_info(dirname)
        graphname = "pamplona.jpeg"
        force_local_graph = self.h.graph_local(testname, graphname)
        nexttest = self.h.next_test(testname, batch)
        prevtest = self.h.prev_test(testname, batch)

        diag = self.h.get_diag_graphs(testname)

        return render_template(
            "result_guess.html",
            batch=batch,
            graphname=graphname,
            leancorrectly=guessstats["leancorrectly"],
            guessedcorrectly=guessstats["guessedcorrectly"],
            isconfidence=guessstats["isconfidence"],
            win_by=stats["win_by"],
            atleast=stats["lowerbound"],
            atmost=stats["upperbound"],
            winner=guessstats["winner"],
            loser=guessstats["loser"],
            testname=testname,
            nexttest=nexttest,
            prevtest=prevtest,
            tables=tables,
            diagnostic_graphs=diag,
            diagnostic_charts=diagnostic_charts,
            description=info,
            force_local_graph=force_local_graph,
            dollar_pct=stats["dollar_pct"],
            lower_dollar=stats["lower_dollar"],
            upper_dollar=stats["upper_dollar"],
            campaign=stats["campaign"],
        )

    def ask_guess(self, testname, batch):
        # Ask the user to guess a winner
        # Only in guess mode
        winner_row, dirname = self.h.win_dir(testname)
        screenshotlines = self.h.screenshot_lines(dirname)
        if screenshotlines["error"]:
            return (
                render_template(
                    "error.html",
                    batch=batch,
                    why=screenshotlines["why"],
                    title="404'd!",
                ),
                404,
            )
        else:
            screenshotlines = screenshotlines["lines"]

        screenshots, longnames, manytype = self.h.find_screenshots_and_names(
            dirname, screenshotlines
        )
        stats = self.h.row_stats(winner_row)
        guessnone = self.h.get_guessnone()
        info = self.h.get_info(dirname)

        return render_template(
            "guess.html",
            manytype=manytype,
            batch=batch,
            testname=testname,
            imgs=screenshots,
            longnames=longnames,
            guessnone=guessnone,
            date=stats["date"],
            description=info,
        )

    def show_noguess(self, testname, batch):
        # Show the stats, screenshots, etc all in the same page
        winner_row, dirname = self.h.win_dir(testname)
        if winner_row is None:
            return render_template(
                "error.html", batch=batch, why="Incorrect Test Name", secret=winner_row
            )

        if not self.h.test_in_batch(testname, batch):
            return (
                render_template(
                    "error.html",
                    batch=batch,
                    why="Ordering scheme: " + batch + " not found",
                    title="Err...",
                ),
                404,
            )

        screenshotlines = self.h.screenshot_lines(dirname)
        if screenshotlines["error"]:
            return (
                render_template(
                    "error.html",
                    batch=batch,
                    why=screenshotlines["why"],
                    title="404'd!",
                ),
                404,
            )
        else:
            screenshotlines = screenshotlines["lines"]

        screenshots, longnames, manytype = self.h.find_screenshots_and_names(
            dirname, screenshotlines
        )
        stats = self.h.row_stats(winner_row)
        guessstats = self.h.guess_stats(winner_row, dirname)
        tables = self.h.get_tables(dirname)
        diagnostic_charts = self.h.get_diagnostic_charts(dirname)
        info = self.h.get_info(dirname)
        graphname = "pamplona.jpeg"
        force_local_graph = self.h.graph_local(testname, graphname)
        nexttest = self.h.next_test(testname, batch)
        prevtest = self.h.prev_test(testname, batch)

        diag = self.h.get_diag_graphs(testname)

        return render_template(
            "result_noguess.html",
            batch=batch,
            graphname=graphname,
            isconfidence=guessstats["isconfidence"],
            win_by=stats["win_by"],
            atleast=stats["lowerbound"],
            atmost=stats["upperbound"],
            winner=guessstats["winner"],
            loser=guessstats["loser"],
            testname=testname,
            nexttest=nexttest,
            prevtest=prevtest,
            tables=tables,
            diagnostic_graphs=diag,
            description=info,
            diagnostic_charts=diagnostic_charts,
            force_local_graph=force_local_graph,
            manytype=manytype,
            imgs=screenshots,
            longnames=longnames,
            dollar_pct=stats["dollar_pct"],
            lower_dollar=stats["lower_dollar"],
            upper_dollar=stats["upper_dollar"],
            campaign=stats["campaign"],
        )

    def show_dir(self, batch, MODE):
        # show dirname
        # Depending on the mode, do or don't display certain bits.

        # Only support chronological and reverse for now
        if batch not in ["chronological", "reverse"]:
            logger.error(
                f"Unsupported batch type: {batch}. Only 'chronological' and 'reverse' are supported."
            )
            return (
                render_template(
                    "error.html",
                    batch=batch,
                    why=f"Batch type '{batch}' not supported. Use 'chronological' or 'reverse'.",
                    title="Unsupported Batch",
                ),
                400,
            )

        # Check if we have the base processed data cached
        if (
            hasattr(self, "_show_dir_base_cache")
            and "base_data" in self._show_dir_base_cache
        ):
            logger.info(f"Using cached base data for {batch}")
            base_data = self._show_dir_base_cache["base_data"]

            # Reorder the data based on the batch
            if batch == "reverse":
                # Reverse the order of all the data
                reordered_data = {
                    "list": list(reversed(base_data["list"])),
                    "allshots": {
                        test: base_data["allshots"][test]
                        for test in reversed(base_data["list"])
                    },
                    "allnames": {
                        test: base_data["allnames"][test]
                        for test in reversed(base_data["list"])
                    },
                    "alldates": {
                        test: base_data["alldates"][test]
                        for test in reversed(base_data["list"])
                    },
                    "allresults": {
                        test: base_data["allresults"][test]
                        for test in reversed(base_data["list"])
                    },
                    "allvarnames": {
                        test: base_data["allvarnames"][test]
                        for test in reversed(base_data["list"])
                    },
                }
            else:
                # Use chronological order (original order)
                reordered_data = base_data

            # Render template with reordered data
            if MODE == "NOGUESS":
                template = "directory_noguess.html"
            else:
                template = "directory_guess.html"

            return render_template(template, mode=MODE, batch=batch, **reordered_data)

        # If no base cache, process everything once
        logger.info(f"Processing base data - this may take a while")

        # Get chronological test list (this is now fast due to caching)
        showthese = self.h.all_tests("chronological")

        # Process all the expensive data once
        allshots = {}
        allnames = {}
        alldates = {}
        allresults = {}
        allvarnames = {}

        for test in showthese:
            winner_row, dirname = self.h.win_dir(test)
            try:
                with open(join(dirname, "screenshots.csv"), "r") as fin:
                    reader = csv.reader(fin, delimiter=",")
                    next(reader)  # Skip header
                    lines = list(reader)
                    screenshots, longnames, manytype = (
                        self.h.find_screenshots_and_names(dirname, lines)
                    )
                    allshots[test] = screenshots
                    allnames[test] = longnames
                    result = self.h.row_stats(winner_row)
                    date = result["date"]
                    alldates[test] = date
                    allvarnames[test] = result["variable"]
                    result["winner"] = winner_row["winner"]
                    result["loser"] = winner_row["loser"]
                    allresults[test] = result
            except Exception as e:
                logger.error(f"Error processing test {test}: {e}")
                continue

        # Cache the base processed data
        base_data = {
            "list": showthese,
            "allshots": allshots,
            "allnames": allnames,
            "alldates": alldates,
            "allresults": allresults,
            "allvarnames": allvarnames,
        }

        if not hasattr(self, "_show_dir_base_cache"):
            self._show_dir_base_cache = {}
        self._show_dir_base_cache["base_data"] = base_data
        logger.info("Cached base data")

        # Now return the appropriate order
        if batch == "reverse":
            # Return reverse order
            reordered_data = {
                "list": list(reversed(showthese)),
                "allshots": {test: allshots[test] for test in reversed(showthese)},
                "allnames": {test: allnames[test] for test in reversed(showthese)},
                "alldates": {test: alldates[test] for test in reversed(showthese)},
                "allresults": {test: allresults[test] for test in reversed(showthese)},
                "allvarnames": {
                    test: allvarnames[test] for test in reversed(showthese)
                },
            }
        else:
            # Return chronological order
            reordered_data = base_data

        # Render template
        if MODE == "NOGUESS":
            template = "directory_noguess.html"
        else:
            template = "directory_guess.html"

        try:
            result = render_template(template, mode=MODE, batch=batch, **reordered_data)
            return result
        except Exception as e:
            logger.error(f"Template rendering error: {e}")
            return (
                render_template(
                    "error.html",
                    batch=batch,
                    why="Error rendering template",
                    title="Error",
                ),
                500,
            )
